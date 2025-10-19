from celery import shared_task, states
from celery.exceptions import Ignore
from agents.agent_extrator.processador_pdf import AgentExtrator
from agents.agent_fraud_analysis.analyzer import AgentFraudCompliance
from .repositories.pessoa_repository import PessoaRepository
from .repositories.classificacao_repository import ClassificacaoRepository


@shared_task(bind=True)
def processar_pdf_task(self, pdf_content_bytes):
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Agente 1 (Gemini) está extraindo os dados...'})
        agente_extrator = AgentExtrator()
        dados_extraidos = agente_extrator.executar(pdf_content_bytes)

        self.update_state(state='PROGRESS', meta={'status': 'Agente 2 (OpenAI) está auditando os riscos...'})
        agente_analista = AgentFraudCompliance(dados_extraidos)
        analise_risco = agente_analista.analisar()

        self.update_state(state='PROGRESS', meta={'status': 'Validando com o banco de dados...'})
        pessoa_repo = PessoaRepository()
        classificacao_repo = ClassificacaoRepository()

        fornecedor_id = pessoa_repo.find_by_documento(dados_extraidos['fornecedor']['cnpj'])
        faturado_id = pessoa_repo.find_by_documento(dados_extraidos['faturado']['cpf/cnpj'])

        classificacoes_validadas = []
        for desc in dados_extraidos['classificacoes_despesa']:
            class_id = classificacao_repo.find_by_descricao(desc)
            classificacoes_validadas.append({
                                                'status': 'EXISTE', 'id': class_id, 'detail': {'descricao': desc}
                                            } if class_id else {
                'status': 'NÃO EXISTE', 'id': None, 'detail': {'descricao': desc}
            })

        validacao_db = {
            'fornecedor': {'status': 'EXISTE', 'id': fornecedor_id,
                           'detail': dados_extraidos['fornecedor']} if fornecedor_id else {'status': 'NÃO EXISTE',
                                                                                           'id': None,
                                                                                           'detail': dados_extraidos[
                                                                                               'fornecedor']},
            'faturado': {'status': 'EXISTE', 'id': faturado_id,
                         'detail': dados_extraidos['faturado']} if faturado_id else {'status': 'NÃO EXISTE', 'id': None,
                                                                                     'detail': dados_extraidos[
                                                                                         'faturado']},
            'classificacoes': classificacoes_validadas,
        }

        return {
            'extracted_data': dados_extraidos,
            'risk_analysis': analise_risco,
            'validation_results': validacao_db
        }
    except Exception as e:
        self.update_state(state=states.FAILURE, meta={'exc_type': type(e).__name__, 'exc_message': str(e),
                                                      'status': f'Falha no processamento: {str(e)}'})
        raise Ignore()
