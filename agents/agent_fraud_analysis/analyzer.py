import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class AgentFraudCompliance:

    def __init__(self, extracted_data, api_key=None):
        # Prioriza a chave passada (da sessão), senão tenta o .env (backup)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            print("Aviso: API Key do Gemini não fornecida para o Analista de Risco.")

        self.data = extracted_data

    def analisar(self):
        if not self.api_key:
            raise ValueError("Chave da API do Gemini não configurada. Por favor, configure no menu.")

        genai.configure(api_key=self.api_key)
        # Usamos o modelo Flash para ser rápido e barato
        model = genai.GenerativeModel(
            'gemini-2.5-flash', 
            generation_config={"response_mime_type": "application/json"}
        )

        hoje = datetime.now().strftime("%Y-%m-%d")

        system_prompt = f"""
            Você é um analista de risco financeiro sênior.
            
            CONTEXTO TEMPORAL:
            - Hoje é: {hoje}
            - Use esta data para validar se a emissão é futura ou passada.
            
            TAREFA:
            Analise os dados extraídos da nota fiscal e gere um parecer técnico em JSON.
            
            DADOS DA NOTA:
            {json.dumps(self.data, indent=2, ensure_ascii=False)}

            CRITÉRIOS:
            1. Validade Temporal: Data de emissão maior que {hoje} é suspeito.
            2. Inconsistência: Produtos vs Categoria.
            3. Preços: Valores fora de mercado.
            4. Padrões Suspeitos.

            FORMATO JSON OBRIGATÓRIO:
            {{
              "risk_score": <int, 0-10>,
              "summary": "<string, resumo>",
              "red_flags": [
                {{ "type": "<string>", "description": "<string>" }}
              ]
            }}
        """

        try:
            response = model.generate_content(system_prompt)
            return json.loads(response.text)
        except Exception as e:
            return {
                "risk_score": 0,
                "summary": f"Erro na análise automática: {str(e)}",
                "red_flags": []
            }