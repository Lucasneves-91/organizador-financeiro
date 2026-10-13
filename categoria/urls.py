from django.urls import path

from . import views

app_name = 'categoria'

urlpatterns = [
    path('', views.lista_categorias, name='lista_categorias'),
    path('nova/', views.cadastrar_categoria, name='cadastrar_categoria'),
    path('<int:categoria_id>/editar/', views.editar_categoria, name='editar_categoria'),
    path('<int:categoria_id>/excluir/', views.excluir_categoria, name='excluir_categoria'),

    path('regras/', views.lista_regras, name='lista_regras'),
    path('regras/nova/', views.cadastrar_regra, name='cadastrar_regra'),
    path('regras/<int:regra_id>/editar/', views.editar_regra, name='editar_regra'),
    path('regras/<int:regra_id>/excluir/', views.excluir_regra, name='excluir_regra'),
]
