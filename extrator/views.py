# INÍCIO DOS IMPORTS ADICIONADOS
import json
from agents.agent_rag.consultor_simples import AgentConsultorSimples
from agents.agent_rag.consultor_embeddings import AgentConsultorEmbeddings
# FIM DOS IMPORTS ADICIONADOS

from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from celery.result import AsyncResult
from .tasks import processar_pdf_task
from .repositories.pessoa_repository import PessoaRepository
from .repositories.classificacao_repository import ClassificacaoRepository
from .repositories.movimento_repository import MovimentoRepository


def upload_view(request):
    return render(request, 'upload.html')


def processar_pdf_view(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            return JsonResponse({'error': 'Nenhum arquivo enviado.'}, status=400)
        pdf_content_bytes = pdf_file.read()
        task = processar_pdf_task.delay(pdf_content_bytes)
        return JsonResponse({'task_id': task.id})
    return JsonResponse({'error': 'Método inválido.'}, status=405)


def task_status_view(request, task_id):
    task_result = AsyncResult(task_id)

    response_data = {
        'state': task_result.state,
        'status': '',
        'error_message': None,
        'result': None
    }

    if task_result.state == 'PENDING':
        response_data['status'] = 'A tarefa está na fila para ser processada...'

    elif task_result.state == 'PROGRESS':
        if isinstance(task_result.info, dict):
            response_data['status'] = task_result.info.get('status', 'Processando...')
        else:
            response_data['status'] = 'Processando...'

    elif task_result.state == 'SUCCESS':
        response_data['result'] = task_result.result
        request.session['full_result'] = task_result.result

    elif task_result.state == 'FAILURE':
        if isinstance(task_result.info, dict):
            error_msg = task_result.info.get('exc_message', 'Erro desconhecido na tarefa.')
        else:
            error_msg = str(task_result.info)

        response_data['status'] = 'Ocorreu um erro no processamento.'
        response_data['error_message'] = error_msg

    return JsonResponse(response_data)


def confirmar_lancamento_view(request):
    if request.method == 'POST':
        full_result = request.session.get('full_result')
        if not full_result:
            return JsonResponse({'error': 'Sessão expirada.'}, status=400)

        dados = full_result.get('extracted_data')
        validacao = full_result.get('validation_results')
        items_criados = []

        try:
            with transaction.atomic():
                pessoa_repo = PessoaRepository()
                class_repo = ClassificacaoRepository()
                mov_repo = MovimentoRepository()

                fornecedor_id = validacao['fornecedor']['id']
                if not fornecedor_id:
                    fornecedor_id = pessoa_repo.create('FORNECEDOR', dados['fornecedor'])
                    items_criados.append(f"Fornecedor: {dados['fornecedor']['razao_social']}")

                faturado_id = validacao['faturado']['id']
                if not faturado_id:
                    faturado_id = pessoa_repo.create('FATURADO', dados['faturado'])
                    items_criados.append(f"Faturado: {dados['faturado']['nome_completo']}")

                classificacao_ids = []
                for class_val in validacao['classificacoes']:
                    class_id = class_val['id']
                    if not class_id:
                        class_id = class_repo.create('DESPESA', class_val['detail']['descricao'])
                        items_criados.append(f"Classificação: {class_val['detail']['descricao']}")
                    classificacao_ids.append(class_id)

                mov_id = mov_repo.create_completo(dados, dados['parcelas'], fornecedor_id, faturado_id, classificacao_ids)
                items_criados.append(f"Movimento Financeiro #{mov_id}")

            del request.session['full_result']
            return JsonResponse({'success': True, 'message': f"Lançamento #{mov_id} criado!", 'created_items': items_criados})
        except Exception as e:
            return JsonResponse({'error': f'Erro ao salvar: {e}'}, status=500)
    return redirect(reverse('upload_view'))


def pessoa_list_view(request):
    repo = PessoaRepository()
    pessoas_raw = repo.list_all()
    pessoas = [{'id': p[0], 'razaosocial': p[1], 'documento': p[2], 'tipo': p[3], 'status': p[4]} for p in pessoas_raw]
    return render(request, 'pessoa_list.html', {'pessoas': pessoas})


def pessoa_form_view(request, pk=None):
    repo = PessoaRepository()
    if request.method == 'POST':
        if pk:
            repo.update(pk, request.POST['tipo'], request.POST['razaosocial'], request.POST['fantasia'],
                        request.POST['documento'])
        else:
            detail = {'tipo': request.POST['tipo'], 'razaosocial': request.POST['razaosocial'],
                      'fantasia': request.POST['fantasia'], 'documento': request.POST['documento']}
            repo.create(request.POST['tipo'], detail)
        return redirect('pessoa_list')

    pessoa = None
    if pk:
        pessoa_raw = repo.find_by_id(pk)
        pessoa = {'id': pessoa_raw[0], 'tipo': pessoa_raw[1], 'razaosocial': pessoa_raw[2], 'fantasia': pessoa_raw[3],
                  'documento': pessoa_raw[4]}
    return render(request, 'pessoa_form.html', {'pessoa': pessoa})


def pessoa_toggle_status_view(request, pk):
    repo = PessoaRepository()
    repo.toggle_status(pk)
    return redirect('pessoa_list')


def classificacao_list_view(request):
    repo = ClassificacaoRepository()
    classificacoes_raw = repo.list_all()
    classificacoes = [{'id': c[0], 'descricao': c[1], 'tipo': c[2], 'status': c[3]} for c in classificacoes_raw]
    return render(request, 'classificacao_list.html', {'classificacoes': classificacoes})


def classificacao_form_view(request, pk=None):
    repo = ClassificacaoRepository()
    if request.method == 'POST':
        if pk:
            repo.update(pk, request.POST['tipo'], request.POST['descricao'])
        else:
            repo.create(request.POST['tipo'], request.POST['descricao'])
        return redirect('classificacao_list')

    classificacao = None
    if pk:
        class_raw = repo.find_by_id(pk)
        classificacao = {'id': class_raw[0], 'tipo': class_raw[1], 'descricao': class_raw[2]}
    return render(request, 'classificacao_form.html', {'classificacao': classificacao})


def classificacao_toggle_status_view(request, pk):
    repo = ClassificacaoRepository()
    repo.toggle_status(pk)
    return redirect('classificacao_list')


def movimento_receber_create_view(request):
    pessoa_repo = PessoaRepository()
    class_repo = ClassificacaoRepository()

    if request.method == 'POST':
        mov_repo = MovimentoRepository()
        movimento_data = {
            'numeronotafiscal': request.POST.get('numeronotafiscal'),
            'dataemissao': request.POST.get('dataemissao'),
            'descricao': request.POST.get('descricao')
        }
        cliente_id = request.POST.get('cliente')
        classificacoes_ids = request.POST.getlist('classificacoes')

        parcelas_data = []
        indices = [key.split('-')[1] for key in request.POST if key.startswith('identificacao-')]
        for i in indices:
            parcelas_data.append({
                'identificacao': request.POST.get(f'identificacao-{i}'),
                'datavencimento': request.POST.get(f'datavencimento-{i}'),
                'valorparcela': float(request.POST.get(f'valorparcela-{i}'))
            })

        try:
            total_parcelas = sum(p['valorparcela'] for p in parcelas_data)
            cliente_obj = pessoa_repo.find_by_id(cliente_id)
            cliente_nome = cliente_obj[2] if cliente_obj else "Cliente não encontrado"

            mov_repo.create_recebimento(movimento_data, parcelas_data, cliente_id, classificacoes_ids)

            messages.success(request,
                             f"<strong>Sucesso!</strong> Conta a Receber para o cliente <strong>{cliente_nome}</strong> no valor total de <strong>R$ {total_parcelas:.2f}</strong> foi cadastrada.")

            return redirect('movimento_list')
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao cadastrar a conta: {e}")

    clientes_raw = pessoa_repo.list_active_clients()
    receitas_raw = class_repo.list_active_receitas()

    context = {
        'clientes': [{'id': c[0], 'razaosocial': c[1]} for c in clientes_raw],
        'receitas': [{'id': r[0], 'descricao': r[1]} for r in receitas_raw]
    }
    return render(request, 'movimento_receber_form.html', context)


def movimento_list_view(request):
    repo = MovimentoRepository()
    movimentos_raw = repo.list_all_movements()
    movimentos = [
        {
            'id': m[0], 'dataemissao': m[1], 'numeronotafiscal': m[2],
            'tipo': m[3], 'fornecedor_cliente': m[4], 'faturado': m[5],
            'valortotal': m[6], 'status': m[7]
        } for m in movimentos_raw
    ]
    context = {'movimentos': movimentos}
    return render(request, 'movimento_list.html', context)


# INÍCIO DO CÓDIGO ADICIONADO
def rag_simples_view(request):
    """Renderiza a página de consulta RAG Simples."""
    return render(request, 'rag_simples.html')

def processar_rag_simples_view(request):
    """Processa a consulta RAG Simples."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pergunta = data.get('pergunta')

            if not pergunta:
                return JsonResponse({'error': 'Nenhuma pergunta fornecida.'}, status=400)

            agent = AgentConsultorSimples()
            resposta = agent.executar(pergunta)

            return JsonResponse({'resposta': resposta})

        except Exception as e:
            return JsonResponse({'error': f'Erro no servidor: {e}'}, status=500)

    return JsonResponse({'error': 'Método inválido.'}, status=405)

def rag_embeddings_view(request):
    """Renderiza a página de consulta RAG Embeddings."""
    return render(request, 'rag_embeddings.html')

def processar_rag_embeddings_view(request):
    """Processa a consulta RAG Embeddings."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pergunta = data.get('pergunta')

            if not pergunta:
                return JsonResponse({'error': 'Nenhuma pergunta fornecida.'}, status=400)

            agent = AgentConsultorEmbeddings()
            resposta = agent.executar(pergunta)

            return JsonResponse({'resposta': resposta})

        except Exception as e:
            return JsonResponse({'error': f'Erro no servidor: {e}'}, status=500)

    return JsonResponse({'error': 'Método inválido.'}, status=405)
