from django.core.exceptions import ValidationError
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Sum
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from django.contrib import messages
import json

# Importamos los formularios y modelos necesarios
from .forms import UserRoleForm, ObraDeArteForm, RestauracionForm, ExhibicionForm, CesionForm
from .models import (
    Sala, Periodo, Estilo, Tecnica, Material, ObraDeArte, 
    Restaurador, Restauracion, MuseoColaborador, Cesion, Exhibicion, 
    TelefonoMuseo, EmailMuseo, SolicitudCesion, ObraSolicitada
)

# --- Acción personalizada ---
@admin.action(description="Enviar seleccionados a restauración")
def enviar_a_restauracion(modeladmin, request, queryset):
    queryset.update(estado='RE')

# --- Definiciones de Inlines ---
class RestauracionInline(admin.TabularInline):
    model = Restauracion
    extra = 0
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'tipo_restauracion', 'informe_danos', 'restauradores_asignados')
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

class TelefonoMuseoInline(admin.TabularInline):
    model = TelefonoMuseo
    extra = 0
    min_num = 1 

class EmailMuseoInline(admin.TabularInline):
    model = EmailMuseo
    extra = 0
    min_num = 1

class ObraSolicitadaInline(admin.TabularInline):
    model = ObraSolicitada
    extra = 0 
    min_num = 1 # Exige al menos una obra, haciéndola obligatoria

# --- Clases de Administración Personalizadas ---

# Nota: El registro de User se hace más abajo, quitando primero el por defecto
class UserAdmin(BaseUserAdmin):
    form = UserRoleForm

@admin.register(ObraDeArte)
class ObraDeArteAdmin(admin.ModelAdmin):
    form = ObraDeArteForm
    list_display = ('titulo', 'autor', 'estado', 'tipo_obra', 'sala')
    list_filter = ('estado', 'tipo_obra', 'sala', 'periodo')
    search_fields = ('titulo', 'autor')
    inlines = [RestauracionInline]
    change_list_template = "admin/obradearte_changelist.html"
    actions = [enviar_a_restauracion]
    filter_horizontal = ('tecnica', 'material', 'estilo')

    fieldsets = (
        ('Información Principal', {
            'fields': ('titulo', 'imagen', 'autor')
        }),
        ('Datos Históricos y Económicos', {
            'fields': ('valoracion_economica', 'fecha_creacion', 'fecha_entrada_museo', 'periodo')
        }),
        ('Clasificación y Ubicación', {
            'fields': ('estado', 'tipo_obra', 'tecnica', 'material', 'estilo', 'sala')
        }),
    )

    def get_list_display(self, request):
        display = list(self.list_display)
        if not request.user.groups.filter(name='Restauradores Jefes').exists():
            display.append('valoracion_economica')
        return display
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.user.groups.filter(name='Directores').exists():
            if 'enviar_a_restauracion' in actions:
                del actions['enviar_a_restauracion']
        return actions

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reporte-mantenimiento/', self.admin_site.admin_view(self.reporte_mantenimiento_view), name='reporte_mantenimiento'),
            path('reporte-valoracion/', self.admin_site.admin_view(self.reporte_valoracion_view), name='reporte_valoracion')
        ]
        return custom_urls + urls

    def reporte_mantenimiento_view(self, request):
        obras_necesitadas = [obra for obra in ObraDeArte.objects.all() if obra.anios_desde_ultima_restauracion >= 5]
        context = dict(self.admin_site.each_context(request), obras_para_mantenimiento=obras_necesitadas)
        return render(request, "admin/reporte_mantenimiento.html", context)

    def reporte_valoracion_view(self, request):
        calculo = ObraDeArte.objects.aggregate(total_valor=Sum('valoracion_economica'))
        total = calculo['total_valor'] or 0
        context = dict(self.admin_site.each_context(request), total_valor=total)
        return render(request, "admin/reporte_valoracion.html", context)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Si el usuario está en el grupo "Restauradores Jefes"...
        if request.user.groups.filter(name='Restauradores Jefes').exists():
            # ...creamos una nueva lista de fieldsets sin el campo de valoración.
            new_fieldsets = []
            for name, options in fieldsets:
                # Copiamos la lista de campos y quitamos el que no queremos
                fields_list = list(options.get('fields', []))
                if 'valoracion_economica' in fields_list:
                    fields_list.remove('valoracion_economica')

                # Reconstruimos el fieldset con los campos filtrados
                new_options = options.copy()
                new_options['fields'] = fields_list
                new_fieldsets.append((name, new_options))
            return new_fieldsets

        # Si no es un Restaurador Jefe, devolvemos los fieldsets originales.
        return fieldsets

@admin.register(Restauracion)
class RestauracionAdmin(admin.ModelAdmin):
    form = RestauracionForm
    list_display = ('obra_a_restaurar', 'fecha_inicio', 'fecha_fin')
    autocomplete_fields = ['obra_a_restaurar']
    filter_horizontal = ['restauradores_asignados']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.fecha_fin:
            obj.obra_a_restaurar.estado = 'EX'
        else:
            obj.obra_a_restaurar.estado = 'RE'
        obj.obra_a_restaurar.save()
        
        restauradores = form.cleaned_data['restauradores_asignados']
        if obj.fecha_fin:
            # Si se completa, debemos liberar a los restauradores,
            # pero comprobando si no están en OTRA restauración activa.
            for r in restauradores:
                if not r.restauracion_set.filter(fecha_fin__isnull=True).exists():
                    r.ocupado = False
                    r.save()
        else:
            restauradores.update(ocupado=True)

@admin.register(Restaurador)
class RestauradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'email', 'especialidad', 'estado_general')
    search_fields = ('nombre', 'apellidos', 'email')
    list_filter = ('estado', 'ocupado', 'especialidad')
    
    @admin.display(description='Disponibilidad')
    def estado_general(self, obj):
        if obj.estado == 'I': return 'Inactivo'
        return 'En restauración' if obj.ocupado else 'Libre'

@admin.register(MuseoColaborador)
class MuseoColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'pais', 'ver_catalogo')
    search_fields = ('nombre', 'ciudad', 'pais')
    inlines = [TelefonoMuseoInline, EmailMuseoInline]

    @admin.display(description="Catálogo Externo")
    def ver_catalogo(self, obj):
        if obj.enlace_catalogo:
            return format_html(f'<a href="{obj.enlace_catalogo}" target="_blank">Ver Catálogo</a>')
        return "No disponible"

@admin.register(Cesion)
class CesionAdmin(admin.ModelAdmin):
    # 1. Conectamos nuestro formulario de validación
    form = CesionForm

    # 2. Configuración visual
    list_display = ('__str__', 'museo_destino', 'fecha_inicio', 'fecha_fin')
    filter_horizontal = ('obras_cedidas',)
    list_filter = ('museo_destino',)

    # 3. La lógica de automatización se queda aquí
    def save_model(self, request, obj, form, change):
        # Primero, guardamos la cesión
        super().save_model(request, obj, form, change)

        # Luego, cambiamos el estado de las obras (esto ya no causa recursión)
        obras_seleccionadas = form.cleaned_data['obras_cedidas']
        obras_seleccionadas.update(estado='CE')


@admin.register(SolicitudCesion)
class SolicitudCesionAdmin(admin.ModelAdmin):
    # Mostramos los campos principales en la lista
    list_display = ('__str__', 'fecha_inicio_solicitud', 'fecha_fin_solicitud')
    list_filter = ('museo_origen',)
    autocomplete_fields = ['museo_origen']

    # Usamos el inline para añadir obras en filas separadas
    inlines = [ObraSolicitadaInline]

    # Mantenemos estos métodos para que el botón dinámico "Ver Catálogo" funcione
    def add_view(self, request, form_url='', extra_context=None):
        museos = MuseoColaborador.objects.all()
        museos_data = {museo.id: museo.enlace_catalogo for museo in museos}
        extra_context = extra_context or {}
        extra_context['museos_data_json'] = json.dumps(museos_data)
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        museos = MuseoColaborador.objects.all()
        museos_data = {museo.id: museo.enlace_catalogo for museo in museos}
        extra_context = extra_context or {}
        extra_context['museos_data_json'] = json.dumps(museos_data)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(Exhibicion)
class ExhibicionAdmin(admin.ModelAdmin):
    form = ExhibicionForm # <-- AÑADE ESTA LÍNEA
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin')
    filter_horizontal = ('obras_incluidas',)

# --- Registros de Modelos Simples y el de User ---
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Sala)
admin.site.register(Periodo)
admin.site.register(Estilo)
admin.site.register(Tecnica)
admin.site.register(Material)