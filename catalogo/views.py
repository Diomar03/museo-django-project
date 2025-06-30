from django.shortcuts import render, get_object_or_404
from .models import ObraDeArte, Sala, Periodo, Estilo, Exhibicion
from django.core.paginator import Paginator # Para la paginación
from django.db.models import Q # Búsquedas complejas

def inicio(request):
    # Obtenemos todas las exhibiciones para el carrusel
    exhibiciones = Exhibicion.objects.all()

    # Obtenemos las 6 obras más recientes que estén en exposición
    obras_recientes = ObraDeArte.objects.filter(estado='EX').order_by('-fecha_entrada_museo')[:6]

    context = {
        'exhibiciones': exhibiciones,
        'obras_recientes': obras_recientes,
    }
    return render(request, 'catalogo/inicio.html', context)

def nosotros(request):
    # Esta vista por ahora solo renderiza la plantilla
    return render(request, 'catalogo/nosotros.html')

def lista_obras(request):
    obras = ObraDeArte.objects.filter(estado='EX').order_by('titulo')

    salas = Sala.objects.all()
    periodos = Periodo.objects.all()
    estilos = Estilo.objects.all()

    # Lógica de Búsqueda y Filtrado
    query = request.GET.get('q')
    sala_seleccionada_id = request.GET.get('sala')
    periodo_seleccionado_id = request.GET.get('periodo')
    estilo_seleccionado_id = request.GET.get('estilo')
    tipo_seleccionado = request.GET.get('tipo')

    if query:
        obras = obras.filter(Q(titulo__icontains=query) | Q(autor__icontains=query))
    if sala_seleccionada_id:
        obras = obras.filter(sala__id=sala_seleccionada_id)
    if periodo_seleccionado_id:
        obras = obras.filter(periodo__id=periodo_seleccionado_id)
    if estilo_seleccionado_id:
        obras = obras.filter(estilo__id=estilo_seleccionado_id)
    if tipo_seleccionado:
        obras = obras.filter(tipo_obra=tipo_seleccionado)

    # Lógica de Paginación
    paginator = Paginator(obras, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- NUEVA LÓGICA PARA MANTENER FILTROS EN PAGINACIÓN ---
    # Copiamos los parámetros GET de la URL
    params = request.GET.copy()
    # Si 'page' está en los parámetros, lo quitamos
    if 'page' in params:
        del params['page']
    # Codificamos los parámetros restantes en una cadena de texto
    # El resultado será algo como: "q=grito&sala=1"
    params_url = params.urlencode()

    context = {
        'page_obj': page_obj,
        'salas': salas,
        'periodos': periodos,
        'estilos': estilos,
        'params_url': params_url, # Pasamos la cadena de texto a la plantilla
        # Pasamos los valores para que los filtros recuerden su estado
        'query': query,
        'sala_seleccionada_id': sala_seleccionada_id,
        'periodo_seleccionado_id': periodo_seleccionado_id,
        'estilo_seleccionado_id': estilo_seleccionado_id,
        'tipo_seleccionado': tipo_seleccionado,
    }
    return render(request, 'catalogo/lista_obras.html', context)


# La vista de detalle
def detalle_obra(request, pk):
    # Usamos get_object_or_404 para obtener la obra específica por su ID (pk).
    # Si no la encuentra, Django mostrará automáticamente una página de "No encontrado".
    obra = get_object_or_404(ObraDeArte, pk=pk)

    context = {
        'obra': obra,
    }

    return render(request, 'catalogo/detalle_obra.html', context)