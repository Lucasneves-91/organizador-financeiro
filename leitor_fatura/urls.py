from django.urls import path

from . import views

app_name = 'leitor_fatura'

urlpatterns = [
    path('', views.upload, name='upload'),
    path('faturas/', views.lista_faturas, name='lista_faturas'),
    path('faturas/<int:lote_id>/excluir/', views.excluir_fatura, name='excluir_fatura'),
    path('<int:lote_id>/', views.preview, name='preview'),
    path('<int:lote_id>/confirmar/', views.confirmar, name='confirmar'),
    path('<int:lote_id>/cancelar/', views.cancelar, name='cancelar'),
]
