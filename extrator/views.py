import json
import base64
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from celery.result import AsyncResult
from django.core.management import call_command
from django.contrib.auth.models import User

from agents.agent_rag.consultor_simples import AgentConsultorSimples
from agents.agent_rag.consultor_embeddings import AgentConsultorEmbeddings
from .tasks import processar_pdf_task
from .repositories.pessoa_repository import PessoaRepository
from .repositories.classificacao_repository import ClassificacaoRepository
from .repositories.movimento_repository import MovimentoRepository


def upload_view(request):
    return render(request, 'upload.html')


def processar_pdf_view(request):
    if request.method == 'POST':
        user_api_key = request.session.get('user_api_key')
        if not user_api_key:
            return JsonResponse({'error': 'Chave de API não configurada. Vá em Configurações.'}, status=403)

        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            return JsonResponse({'error': 'Nenhum arquivo enviado.'}, status=400)
        
        pdf_content_bytes = pdf_file.read()
        
        pdf_content_b64 = base64.b64encode(pdf_content_bytes).decode('utf-8')
        
        task = processar_pdf_task.delay(pdf_content_b64, user_api_key)
        
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
        info = task_result.info if isinstance(task_result.info, dict) else {}
        response_data['status'] = info.get('status', 'Processando...')

    elif task_result.state == 'SUCCESS':
        response_data['result'] = task_result.result
        request.session['full_result'] = task_result.result

    elif task_result.state == 'FAILURE':
        if isinstance(task_result.info, Exception):
            error_msg = str(task_result.info)
        elif isinstance(task_result.info, dict):
            error_msg = task_result.info.get('exc_message', 'Erro desconhecido.')
        else:
            error_msg = str(task_result.info)

        response_data['status'] = 'Ocorreu um erro no processamento.'
        response_data['error_message'] = error_msg

    return JsonResponse(response_data)


def confirmar_lancamento_view(request):
    if request.method == 'POST':
        full_result = request.session.get('full_result')
        if not full_result:
            return JsonResponse({'error': 'Sessão expirada ou inválida.'}, status=400)

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
                    items_criados.append(f"Fornecedor criado: {dados['fornecedor']['razao_social']}")

                faturado_id = validacao['faturado']['id']
                if not faturado_id:
                    faturado_id = pessoa_repo.create('FATURADO', dados['faturado'])
                    items_criados.append(f"Faturado criado: {dados['faturado']['nome_completo']}")

                classificacao_ids = []
                for class_val in validacao['classificacoes']:
                    class_id = class_val['id']
                    if not class_id:
                        class_id = class_repo.create('DESPESA', class_val['detail']['descricao'])
                        items_criados.append(f"Classificação criada: {class_val['detail']['descricao']}")
                    classificacao_ids.append(class_id)

                mov_id = mov_repo.create_completo(dados, dados['parcelas'], fornecedor_id, faturado_id, classificacao_ids)
                items_criados.append(f"Movimento Financeiro #{mov_id} lançado com sucesso.")

            del request.session['full_result']
            return JsonResponse({'success': True, 'message': f"Lançamento #{mov_id} realizado!", 'created_items': items_criados})
        
        except Exception as e:
            return JsonResponse({'error': f'Erro ao salvar no banco: {str(e)}'}, status=500)
            
    return redirect(reverse('upload_view'))


# --- Views de RAG (Chat com IA) ---

def rag_simples_view(request):
    return render(request, 'rag_simples.html')

def processar_rag_simples_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pergunta = data.get('pergunta')

            user_api_key = request.session.get('user_api_key')
            if not user_api_key:
                 return JsonResponse({'error': 'Chave API não configurada. Vá em Configurações.'}, status=403)

            agent = AgentConsultorSimples(api_key=user_api_key)
            resposta = agent.executar(pergunta)
            
            return JsonResponse({'resposta': resposta})

        except Exception as e:
            return JsonResponse({'error': f'Erro no servidor: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método inválido.'}, status=405)


def rag_embeddings_view(request):
    return render(request, 'rag_embeddings.html')

def processar_rag_embeddings_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pergunta = data.get('pergunta')
            
            user_api_key = request.session.get('user_api_key')
            if not user_api_key:
                return JsonResponse({'error': 'Chave API não configurada. Vá em Configurações.'}, status=403)

            agent = AgentConsultorEmbeddings(api_key=user_api_key)
            resposta = agent.executar(pergunta)

            return JsonResponse({'resposta': resposta})

        except Exception as e:
            return JsonResponse({'error': f'Erro no servidor: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método inválido.'}, status=405)


# --- Configuração de API ---

def config_api_view(request):
    if request.method == 'POST':
        api_key = request.POST.get('api_key')
        if api_key:
            request.session['user_api_key'] = api_key
            messages.success(request, "Chave da API configurada com sucesso!")
            return redirect('upload_view')
        else:
            messages.error(request, "A chave não pode estar vazia.")
            
    existing_key = request.session.get('user_api_key', '')
    return render(request, 'config_api.html', {'existing_key': existing_key})


# --- Views de CRUD (Pessoas, Movimentos, etc) ---

def pessoa_list_view(request):
    repo = PessoaRepository()
    pessoas_raw = []
    
    termo_busca = request.GET.get('busca', '')
    modo = request.GET.get('modo', '')
    ordenar_por = request.GET.get('ordenar', 'razaosocial')

    if modo == 'todos':
        pessoas_raw = repo.list_all_active(order_by=ordenar_por)
    elif termo_busca:
        pessoas_raw = repo.search_active(termo_busca, order_by=ordenar_por)
    
    pessoas = [{'id': p[0], 'razaosocial': p[1], 'documento': p[2], 'tipo': p[3], 'status': p[4]} for p in pessoas_raw]
    
    return render(request, 'pessoa_list.html', {
        'pessoas': pessoas, 
        'busca_atual': termo_busca,
        'modo_atual': modo,
        'ordenar_atual': ordenar_por
    })

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
    classificacoes_raw = []
    
    termo_busca = request.GET.get('busca', '')
    modo = request.GET.get('modo', '')
    ordenar_por = request.GET.get('ordenar', 'descricao')

    if modo == 'todos':
        classificacoes_raw = repo.list_all(order_by=ordenar_por)
    elif termo_busca:
        classificacoes_raw = repo.search(termo_busca, order_by=ordenar_por)
    
    classificacoes = [{'id': c[0], 'descricao': c[1], 'tipo': c[2], 'status': c[3]} for c in classificacoes_raw]
    
    return render(request, 'classificacao_list.html', {
        'classificacoes': classificacoes,
        'busca_atual': termo_busca,
        'modo_atual': modo,
        'ordenar_atual': ordenar_por
    })

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
                'valorparcela': float(request.POST.get(f'valorparcela-{i}') or 0)
            })

        try:
            total_parcelas = sum(p['valorparcela'] for p in parcelas_data)
            cliente_obj = pessoa_repo.find_by_id(cliente_id)
            cliente_nome = cliente_obj[2] if cliente_obj else "Cliente não encontrado"

            mov_repo.create_recebimento(movimento_data, parcelas_data, cliente_id, classificacoes_ids)

            messages.success(request,
                             f"<strong>Sucesso!</strong> Conta a Receber para <strong>{cliente_nome}</strong> (R$ {total_parcelas:.2f}) cadastrada.")

            return redirect('movimento_list')
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao cadastrar: {str(e)}")

    clientes_raw = pessoa_repo.list_active_clients()
    receitas_raw = class_repo.list_active_receitas()

    context = {
        'clientes': [{'id': c[0], 'razaosocial': c[1]} for c in clientes_raw],
        'receitas': [{'id': r[0], 'descricao': r[1]} for r in receitas_raw]
    }
    return render(request, 'movimento_receber_form.html', context)

def movimento_list_view(request):
    repo = MovimentoRepository()
    movimentos_raw = []
    
    termo_busca = request.GET.get('busca', '')
    modo = request.GET.get('modo', '')
    ordenar_por = request.GET.get('ordenar', '-dataemissao')

    if modo == 'todos':
        movimentos_raw = repo.list_all_movements(order_by=ordenar_por)
    elif termo_busca:
        movimentos_raw = repo.search_movements(termo_busca, order_by=ordenar_por)
    
    movimentos = [
        {
            'id': m[0], 'dataemissao': m[1], 'numeronotafiscal': m[2],
            'tipo': m[3], 'fornecedor_cliente': m[4], 'faturado': m[5],
            'valortotal': m[6], 'status': m[7]
        } for m in movimentos_raw
    ]
    
    return render(request, 'movimento_list.html', {
        'movimentos': movimentos,
        'busca_atual': termo_busca,
        'modo_atual': modo,
        'ordenar_atual': ordenar_por
    })
    
def criar_admin_view(request):
    """
    View TEMPORÁRIA para criar um superusuário.
    """
    try:
        # Verifica se já existe para não dar erro
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@exemplo.com', 'admin123')
            return JsonResponse({'status': 'Sucesso! Usuário "admin" criado com senha "admin123".'})
        else:
            return JsonResponse({'status': 'O usuário "admin" já existe.'})
    except Exception as e:
        return JsonResponse({'error': f'Erro ao criar admin: {str(e)}'}, status=500)

#Função utilizada para popular o banco de dados para testes.
def popular_banco_view(request):
    """
    View secreta para rodar o script de popular o banco via navegador.
    Útil para servidores onde o Shell é pago/bloqueado.
    """

    try:
        # Chama o comando que criamos (popular_banco.py)
        call_command('popular_banco')
        return JsonResponse({'status': 'Sucesso! 200 registros criados no banco.'})
    except Exception as e:
        return JsonResponse({'error': f'Erro ao popular banco: {str(e)}'}, status=500)