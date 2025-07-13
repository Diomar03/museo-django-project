from django.urls import path
from . import views

urlpatterns = [
    # La ruta raíz '' ahora apunta a la nueva vista de INICIO
    path('', views.inicio, name='inicio'),

    # La galería de obras ahora estará en /obras/
    path('obras/', views.lista_obras, name='lista_obras'),

    # El detalle de una obra no cambia
    path('obra/<int:pk>/', views.detalle_obra, name='detalle_obra'),

    # Añadimos la ruta para la página de "Nosotros"
    path('nosotros/', views.nosotros, name='nosotros'),

    # Nueva ruta para el catálogo de un museo colaborador
    path('museos/<int:museo_id>/catalogo/', views.catalogo_externo, name='catalogo_externo'),
]