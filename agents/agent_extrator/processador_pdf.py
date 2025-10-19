import os
import fitz
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()


class AgentExtrator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("A chave da API do Gemini não foi encontrada no arquivo .env.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def executar(self, pdf_stream):
        try:
            pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
            pdf_text = ""
            for page in pdf_document:
                pdf_text += page.get_text()

            if not pdf_text.strip():
                raise Exception("Não foi possível extrair texto do PDF. O arquivo pode estar vazio ou ser uma imagem.")

            prompt = f"""
                Você é um assistente de IA especialista em extrair dados de notas fiscais. Sua tarefa é extrair os campos solicitados e classificar as despesas.

                A ESTRUTURA FINAL DO JSON DEVE SER EXATAMENTE ESTA:
                {{
                  "fornecedor": {{ "razao_social": "string", "fantasia": "string", "cnpj": "string" }},
                  "faturado": {{ "nome_completo": "string", "cpf/cnpj": "string" }},
                  "numero_nota_fiscal": "string",
                  "data_emissao": "string (formato YYYY-MM-DD)",
                  "descricao_produtos": ["string"],
                  "parcelas": [{{ "data_vencimento": "string (formato YYYY-MM-DD)", "valor_total": "float" }}],
                  "classificacoes_despesa": ["string"]
                }}

                REGRAS CRÍTICAS DE EXECUÇÃO:
                1.  **CLASSIFICAÇÃO DE DESPESA (TAREFA PRIORITÁRIA)**:
                    -   O campo 'classificacoes_despesa' DEVE ser uma lista de strings e NÃO PODE ser nulo ou vazio.
                    -   Analise a 'descricao_produtos' e escolha UMA OU MAIS categorias da lista abaixo que se apliquem.
                    -   Se um item não se encaixar perfeitamente (ex: material de escritório), classifique-o como 'ADMINISTRATIVAS'.
                2.  **NOME DO FATURADO**: O campo 'faturado.nome_completo' é obrigatório.
                3.  **DEMAIS REGRAS**: Preencha todos os outros campos. Se um campo opcional não for encontrado, use `null`.

                LISTA DE CATEGORIAS DE DESPESAS:
                - INSUMOS AGRÍCOLAS
                - MANUTENÇÃO E OPERAÇÃO
                - RECURSOS HUMANOS
                - SERVIÇOS OPERACIONAIS
                - INFRAESTRUTURA E UTILIDADES
                - ADMINISTRATIVAS
                - SEGUROS E PROTEÇÃO
                - IMPOSTOS E TAXAS
                - INVESTIMENTOS

                Analise o texto a seguir e retorne APENAS o JSON completo.

                --- TEXTO DA NOTA FISCAL ---
                {pdf_text}
                --- FIM DO TEXTO ---
            """

            response = self.model.generate_content(prompt)
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()

            return json.loads(cleaned_response)

        except Exception as e:
            raise Exception(f"Erro na execução do agente: {e}")
