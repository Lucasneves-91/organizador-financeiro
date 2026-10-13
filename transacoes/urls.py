from django.urls import path

from . import views

app_name = 'transacoes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nova/', views.cadastrar, name='cadastrar'),
    path('<int:transacao_id>/editar/', views.editar, name='editar'),
    path('<int:transacao_id>/excluir/', views.excluir, name='excluir'),
    path('<int:transacao_id>/categoria/', views.atualizar_categoria, name='atualizar_categoria'),
    path('<int:transacao_id>/natureza/', views.atualizar_natureza, name='atualizar_natureza'),
]
