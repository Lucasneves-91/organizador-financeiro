from django.urls import path

from . import views

app_name = 'transacoes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nova/', views.cadastrar, name='cadastrar'),
    path('<int:transacao_id>/editar/', views.editar, name='editar'),
    path('<int:transacao_id>/excluir/', views.excluir, name='excluir'),
]
