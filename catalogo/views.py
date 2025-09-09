import json
from datetime import date
from django.shortcuts import render, get_object_or_404
from .models import ObraDeArte, Exhibicion, Sala, Periodo, Estilo
from django.core.paginator import Paginator # Para la paginación
from django.db.models import Q # Búsquedas complejas
from .models import MuseoColaborador

def inicio(request):
    # 1. Obtenemos solo las exhibiciones activas
    exhibiciones_activas = Exhibicion.objects.filter(
        fecha_inicio__lte=date.today(),
        fecha_fin__gte=date.today()
    )
    
    # 2. Obtenemos las obras más recientes
    obras_recientes = ObraDeArte.objects.filter(estado='EX').order_by('-fecha_entrada_museo')[:6]
    
    # 3. Preparamos los datos de las exhibiciones en un formato claro
    exhibiciones_data = {}
    for ex in exhibiciones_activas:
        obras_list = [{'titulo': obra.titulo, 'autor': obra.autor} for obra in ex.obras_incluidas.all()]
        
        exhibiciones_data[ex.id] = {
            'id': ex.id,
            'nombre': ex.nombre,
            'descripcion': ex.descripcion,
            'fecha_inicio': ex.fecha_inicio.strftime('%d/%m/%Y'),
            'fecha_fin': ex.fecha_fin.strftime('%d/%m/%Y'),
            'imagen_url': ex.imagen.url if ex.imagen else '',
            'obras': obras_list
        }

    context = {
        'exhibiciones_data': exhibiciones_data, # Pasamos el diccionario directamente
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


def catalogo_externo(request, museo_id):
    # Buscamos el museo para poder mostrar su nombre
    museo = get_object_or_404(MuseoColaborador, pk=museo_id)

    context = {
        'museo': museo,
    }
    # Renderizamos una plantilla genérica para todos los catálogos externos
    return render(request, 'catalogo/catalogo_museo_externo.html', context)

def catalogo_externo(request, museo_id):
    museo = get_object_or_404(MuseoColaborador, pk=museo_id)

    # --- Base de datos simulada de obras de arte externas ---
    datos_simulados_museos = {
        # Datos para el Museo con ID = 1
        1: [
            {'titulo': 'La persistencia de la memoria', 'autor': 'Salvador Dalí', 'img': 'https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg'},
            {'titulo': 'El Guernica', 'autor': 'Pablo Picasso', 'img': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Mural_del_Gernika.jpg/500px-Mural_del_Gernika.jpg'},
            {'titulo': 'Impresión, sol naciente', 'autor': 'Claude Monet', 'img': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Monet_-_Impression%2C_Sunrise.jpg/1200px-Monet_-_Impression%2C_Sunrise.jpg'},
        ],
        # Datos para el Museo con ID = 2
        2: [
            {'titulo': 'La joven de la perla', 'autor': 'Johannes Vermeer', 'img': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/800px-1665_Girl_with_a_Pearl_Earring.jpg'},
            {'titulo': 'La ronda de noche', 'autor': 'Rembrandt', 'img': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/La_ronda_de_noche%2C_por_Rembrandt_van_Rijn.jpg/500px-La_ronda_de_noche%2C_por_Rembrandt_van_Rijn.jpg'},
            {'titulo': 'El jardín de las delicias', 'autor': 'El Bosco', 'img': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/El_jard%C3%ADn_de_las_Delicias%2C_de_El_Bosco.jpg/1200px-El_jard%C3%ADn_de_las_Delicias%2C_de_El_Bosco.jpg'},
        ]
    }

    # Obtenemos las obras para el museo actual, o una lista vacía si no está definido
    obras_simuladas = datos_simulados_museos.get(museo_id, [])

    context = {
        'museo': museo,
        'obras_simuladas': obras_simuladas,
    }
    return render(request, 'catalogo/catalogo_museo_externo.html', context)