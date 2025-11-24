import os
import google.generativeai as genai
import json
import numpy as np
from dotenv import load_dotenv
from django.db import connection
import datetime
import decimal

from .corpus_exemplos import CORPUS_EXEMPLOS

load_dotenv()

class AgentConsultorEmbeddings:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("A chave da API do Gemini é obrigatória.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.schema = self._get_db_schema()

        # --- LÓGICA RAG ---
        self.corpus_perguntas = [item['pergunta'] for item in CORPUS_EXEMPLOS]
        self.corpus_queries = [item['query'] for item in CORPUS_EXEMPLOS]
        
        print("Iniciando Agente Consultor EMBEDDINGS...")
        # Nota: A geração de embeddings pode falhar se a chave for inválida na inicialização
        # Mas permitimos instanciar para validação posterior se necessário
        try:
            print("Gerando embeddings para o corpus de exemplos...")
            self.corpus_embeddings = self._gerar_embeddings_corpus(self.corpus_perguntas)
            
            num_exemplos = self.corpus_embeddings.shape[0] if len(self.corpus_embeddings.shape) > 1 else (len(self.corpus_embeddings) if self.corpus_embeddings.size > 0 else 0)
            print(f"Corpus de Embeddings carregado. {num_exemplos} exemplos processados.")
        except Exception as e:
            print(f"Erro ao inicializar embeddings (verifique a API Key): {e}")
            self.corpus_embeddings = np.array([])


    def _get_db_schema(self):
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
          - "Pessoas_idFornecedorCliente" (int): Chave estrangeira para Tabela "Pessoas"
          - "Pessoas_idFaturado" (int): Chave estrangeira para Tabela "Pessoas"
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

    def _gerar_embeddings_corpus(self, textos):
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=textos,
                task_type="RETRIEVAL_QUERY"
            )
            
            if isinstance(result, dict) and 'embedding' in result:
                embeddings = result['embedding']
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    if isinstance(embeddings[0], list):
                        return np.array(embeddings)
                    else:
                        return np.array([embeddings])
                else:
                    return np.array(embeddings) if isinstance(embeddings, list) else np.array([embeddings])
            elif isinstance(result, list):
                embeddings_list = [item['embedding'] if isinstance(item, dict) and 'embedding' in item else item for item in result]
                return np.array(embeddings_list)
            else:
                return np.array(result)
        except Exception as e:
            print(f"Erro ao gerar embeddings do corpus: {e}")
            return np.array([])

    def _encontrar_exemplos_similares(self, pergunta_usuario, k=3):
        if self.corpus_embeddings.size == 0:
            return ""
        try:
            result_usuario = genai.embed_content(
                model="models/embedding-001",
                content=pergunta_usuario,
                task_type="RETRIEVAL_QUERY"
            )
            if isinstance(result_usuario, dict) and 'embedding' in result_usuario:
                embedding_usuario = np.array(result_usuario['embedding'])
            elif isinstance(result_usuario, list) and len(result_usuario) > 0:
                embedding_usuario = np.array(result_usuario[0]['embedding'] if isinstance(result_usuario[0], dict) else result_usuario[0])
            else:
                embedding_usuario = np.array(result_usuario)
            
            if embedding_usuario.ndim > 1:
                embedding_usuario = embedding_usuario.flatten()

            similaridades = np.dot(self.corpus_embeddings, embedding_usuario)
            top_k_indices = np.argsort(similaridades)[-k:]
            
            exemplos_formatados = "\n\n--- EXEMPLOS RELEVANTES ENCONTRADOS ---\n"
            for i in reversed(top_k_indices):
                exemplos_formatados += f"Exemplo de Pergunta: {self.corpus_perguntas[i]}\n"
                exemplos_formatados += f"Exemplo de SQL: {self.corpus_queries[i]}\n---\n"
            return exemplos_formatados
        except Exception as e:
            print(f"Erro ao encontrar exemplos similares: {e}")
            return "\n\n--- ERRO AO BUSCAR EXEMPLOS ---\n"

    def _executar_query_segura(self, query):
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
            return json.dumps(results[:50], ensure_ascii=False) 
        except Exception as e:
            return f"Erro ao executar a consulta: {e}"

    def executar(self, pergunta_usuario):
        try:
            exemplos_relevantes = self._encontrar_exemplos_similares(pergunta_usuario)

            # --- Etapa 1: Gerar o SQL ---
            prompt_sql = f"""
            Você é um assistente especialista em SQL do PostgreSQL.
            Seu trabalho é traduzir a pergunta do usuário em uma consulta SQL com base no esquema do banco de dados fornecido.
            O usuário NÃO conhece o esquema, então use os nomes das tabelas e colunas do esquema.
            Use aspas duplas (ex: "Pessoas") nas tabelas e colunas, pois elas são case-sensitive.
            
            REGRAS CRÍTICAS:
            1. Gere APENAS a consulta SQL.
            2. NÃO inclua '```sql' ou qualquer outra formatação.
            3. Se a pergunta NÃO tiver NENHUMA relação com o banco (ex: "oi", "bom dia"), retorne APENAS a palavra 'INVALIDO'.
            4. **INSENSIBILIDADE DE CASO (MAIS IMPORTANTE):** Para TODAS as comparações de string (em cláusulas `WHERE` ou `JOIN`), 
               use a função `UPPER()` em ambos os lados para garantir que a busca não seja sensível a maiúsculas/minúsculas.
               Exemplo: `WHERE UPPER(T1.descricao) = UPPER('valor do usuário')`

            --- REGRA DE SINÔNIMOS (IMPORTANTE) ---
            - O usuário pode usar o termo "cliente". No banco, isso pode ser `tipo = 'CLIENTE'` ou `tipo = 'FATURADO'`.
            - Se o usuário perguntar por "clientes", gere um SQL que procure por AMBOS: `... WHERE UPPER(tipo) IN ('CLIENTE', 'FATURADO') ...`
            - Se o usuário perguntar especificamente por "faturado", procure apenas `UPPER(tipo) = 'FATURADO'`.
            --- FIM DA REGRA DE SINÔNIMOS ---

            --- ESQUEMA DO BANCO ---
            {self.schema}
            --- FIM DO ESQUEMA ---
            
            {exemplos_relevantes} 
            
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
            REGRAS DE RESPOSTA:
            - Se o SQL for 'INVALIDO' ou o resultado contiver "A pergunta não parece ser uma consulta", 
              explique amigavelmente que você é um assistente focado em dados financeiros (ex: "Olá! Sou um assistente focado em dados. Como posso ajudar com suas finanças?").
            - Se os resultados forem uma lista vazia, diga que "Nenhum dado foi encontrado para essa consulta."
            - Se for um erro (diferente de 'INVALIDO'), explique o erro de forma simples.
            - Se for um número (ex: contagem), responda diretamente.
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