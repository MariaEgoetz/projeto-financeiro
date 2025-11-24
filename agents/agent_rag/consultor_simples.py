import os
import google.generativeai as genai
import json
import datetime
import decimal
from dotenv import load_dotenv
from django.db import connection 

load_dotenv()

class AgentConsultorSimples:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("A chave da API do Gemini é obrigatória.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.schema = self._get_db_schema()

    def _get_db_schema(self):
        """
        Define o esquema do banco de dados que o LLM pode usar.
        Para segurança, definimos manualmente quais tabelas e colunas
        o agente pode "ver" e consultar.
        """
        schema_info = """
        Tabela "Pessoas":
          - id (int): ID único da pessoa
          - tipo (string): Tipo de pessoa (FORNECEDOR, CLIENTE, FATURADO)
          - razaosocial (string): Razão Social ou Nome Completo
          - documento (string): CNPJ ou CPF
          - status (string): ATIVO ou INATIVO

        Tabela "Classificacao":
          - id (int): ID único da classificação
          - tipo (string): Tipo de classificação (DESPESA, RECEITA)
          - descricao (string): Nome da classificação (ex: INSUMOS AGRÍCOLAS)
          - status (string): ATIVO ou INATIVO

        Tabela "MovimentoContas":
          - id (int): ID único do movimento
          - tipo (string): Tipo de movimento (PAGAR, RECEBER)
          - numeronotafiscal (string): Número da NF-e
          - dataemissao (date): Data de emissão
          - valortotal (decimal): Valor total do movimento
          - status (string): PENDENTE, PAGO, CANCELADO
          - "Pessoas_idFornecedorCliente" (int): Chave estrangeira para Tabela "Pessoas" (o fornecedor ou cliente)
          - "Pessoas_idFaturado" (int): Chave estrangeira para Tabela "Pessoas" (quem foi faturado)

        Tabela "ParcelasContas":
          - id (int): ID único da parcela
          - "MovimentoContas_idMovimentoContas" (int): Chave estrangeira para Tabela "MovimentoContas"
          - identificacao (string): Identificação da parcela (ex: 1/3)
          - datavencimento (date): Data de vencimento
          - valorparcela (decimal): Valor da parcela
          - statusparcela (string): PENDENTE, PAGO

        Tabela "MovimentoContas_has_Classificacao":
          - "MovimentoContas_idMovimentoContas" (int): Chave estrangeira para Tabela "MovimentoContas"
          - "Classificacao_idClassificacao" (int): Chave estrangeira para Tabela "Classificacao"
        """
        return schema_info

    def _executar_query_segura(self, query):
            """
            Executa uma consulta SQL de forma segura (somente leitura).
            """
            # Medida de segurança: proibir qualquer comando que modifique dados
            query_lower = query.lower()
            if any(cmd in query_lower for cmd in ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']):
                raise ValueError("Operação SQL perigosa detectada. Apenas consultas SELECT são permitidas.")
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    
                    results = []
                    for row in rows:
                        processed_row = {}
                        for col_name, value in zip(columns, row):
                            if isinstance(value, (datetime.date, datetime.datetime)):
                                processed_row[col_name] = value.isoformat()
                            elif isinstance(value, decimal.Decimal):
                                processed_row[col_name] = float(value)
                            else:
                                processed_row[col_name] = value
                        results.append(processed_row)

                # Limitar a 50 resultados para não sobrecarregar o LLM
                return json.dumps(results[:50], ensure_ascii=False) 
            
            except Exception as e:
                return f"Erro ao executar a consulta: {e}"

    def executar(self, pergunta_usuario):
        try:
            # --- Etapa 1: Gerar o SQL ---
            prompt_sql = f"""
            Você é um assistente especialista em SQL do PostgreSQL.
            Seu trabalho é traduzir a pergunta do usuário em uma consulta SQL com base no esquema do banco de dados fornecido.
            O usuário NÃO conhece o esquema, então use os nomes das tabelas e colunas do esquema.
            Use aspas duplas (ex: "Pessoas") nas tabelas e colunas, pois elas são case-sensitive.
            
            REGRAS CRÍTICAS:
            1. Gere APENAS a consulta SQL.
            2. NÃO inclua '```sql' ou qualquer outra formatação.
            3. Priorize consultas que respondam diretamente à pergunta.
            4. Se a pergunta for sobre "hoje", "este mês", use as funções do PostgreSQL como NOW() ou CURRENT_DATE.
            5. Se a pergunta NÃO tiver NENHUMA relação com o banco de dados (ex: "oi", "bom dia", "quem é você?"), 
               retorne APENAS a palavra 'INVALIDO'.
            6. **INSENSIBILIDADE DE CASO (MAIS IMPORTANTE):** Para TODAS as comparações de string (em cláusulas `WHERE`), 
               use a função `UPPER()` em ambos os lados para garantir que a busca não seja sensível a maiúsculas/minúsculas.
               Exemplo: `WHERE UPPER(coluna) = UPPER('valor do usuário')`

            --- REGRA DE SINÔNIMOS (IMPORTANTE) ---
            - O usuário pode usar o termo "cliente". No banco, isso pode ser `tipo = 'CLIENTE'` ou `tipo = 'FATURADO'`.
            - Se o usuário perguntar por "clientes", gere um SQL que procure por AMBOS: `... WHERE UPPER(tipo) IN ('CLIENTE', 'FATURADO') ...`
            - Se o usuário perguntar especificamente por "faturado", procure apenas `UPPER(tipo) = 'FATURADO'`.
            --- FIM DA REGRA DE SINÔNIMOS ---

            --- ESQUEMA DO BANCO ---
            {self.schema}
            --- FIM DO ESQUEMA ---

            PERGUNTA DO USUÁRIO: "{pergunta_usuario}"

            SQL GERADO:
            """

            response_sql = self.model.generate_content(prompt_sql)

            try:
                sql_query = response_sql.text.strip()
            except ValueError:
                sql_query = 'INVALIDO' 
                
            if not sql_query:
                sql_query = 'INVALIDO'


            # --- Etapa 2: Executar o SQL (ou pular) ---
            if sql_query.upper() == 'INVALIDO':
                sql_results = json.dumps({"erro": "A pergunta não parece ser uma consulta de banco de dados."})
            else:
                sql_results = self._executar_query_segura(sql_query)

            # --- Etapa 3: Gerar a Resposta Final ---
            prompt_final = f"""
            Você é um assistente financeiro amigável.
            A pergunta do usuário foi: "{pergunta_usuario}"
            
            Para responder, eu executei (ou tentei executar) a consulta SQL:
            `{sql_query}`
            
            E obtive os seguintes resultados do banco (em formato JSON):
            {sql_results}

            Com base nesses resultados, elabore uma resposta clara e amigável em português para o usuário.
            
            --- NOVAS REGRAS DE RESPOSTA ---
            - Se o SQL for 'INVALIDO' ou o resultado contiver "A pergunta não parece ser uma consulta", 
              explique amigavelmente que você é um assistente focado em dados financeiros e não entendeu a pergunta 
              (ex: "Olá! Sou um assistente focado em dados. Como posso ajudar com suas finanças?").
            - Se os resultados forem uma lista vazia, diga que "Nenhum dado foi encontrado para essa consulta."
            - Se for um erro (diferente de 'INVALIDO'), explique o erro de forma simples (ex: "Tive um problema ao consultar o banco de dados.").
            - Se for um número (ex: contagem), responda diretamente (ex: "Foram encontrados 5 fornecedores.").
            - Se for uma lista de itens, formate-os de maneira legível.

            RESPOSTA AMIGÁVEL:
            """
            
            response_final = self.model.generate_content(prompt_final)
            
            try:
                return response_final.text
            except ValueError:
                return "Desculpe, tive um problema ao processar a resposta final. Tente novamente."

        except Exception as e:
            return f"Desculpe, ocorreu um erro geral no processamento da sua pergunta: {e}"