from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload_view'),
    path('processar/', views.processar_pdf_view, name='processar_pdf'),
    path('task_status/<str:task_id>/', views.task_status_view, name='task_status'),
    path('confirmar-lancamento/', views.confirmar_lancamento_view, name='confirmar_lancamento'),

    path('pessoas/', views.pessoa_list_view, name='pessoa_list'),
    path('pessoas/nova/', views.pessoa_form_view, name='pessoa_create'),
    path('pessoas/<int:pk>/editar/', views.pessoa_form_view, name='pessoa_update'),
    path('pessoas/<int:pk>/status/', views.pessoa_toggle_status_view, name='pessoa_toggle_status'),

    path('classificacoes/', views.classificacao_list_view, name='classificacao_list'),
    path('classificacoes/nova/', views.classificacao_form_view, name='classificacao_create'),
    path('classificacoes/<int:pk>/editar/', views.classificacao_form_view, name='classificacao_update'),
    path('classificacoes/<int:pk>/status/', views.classificacao_toggle_status_view, name='classificacao_toggle_status'),

    path('contas-a-receber/nova/', views.movimento_receber_create_view, name='movimento_receber_create'),
    path('movimentos/', views.movimento_list_view, name='movimento_list')
]
