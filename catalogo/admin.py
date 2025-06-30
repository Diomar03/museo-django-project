from django.contrib import admin
from django.db.models import Sum
from django.urls import path
from django.shortcuts import render
# Importamos las herramientas para personalizar el admin de User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
# Importamos nuestro formulario personalizado
from .forms import UserRoleForm, ObraDeArteForm, RestauracionForm
from .models import (
    Sala, Periodo, Estilo, Tecnica, Material, ObraDeArte, 
    Restaurador, Restauracion, MuseoColaborador, Cesion, Exhibicion
)

# --- Definimos un nuevo Admin para el modelo User ---
class UserAdmin(BaseUserAdmin):
    # Le decimos que use nuestro formulario en lugar del de por defecto
    form = UserRoleForm

# --- Acción personalizada ---
@admin.action(description="Enviar seleccionados a restauración")
def enviar_a_restauracion(modeladmin, request, queryset):
    queryset.update(estado='RE')


# --- INLINE para mostrar Restauraciones dentro de ObraDeArte ---
class RestauracionInline(admin.TabularInline):
    model = Restauracion
    extra = 0
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'tipo_restauracion', 'informe_danos', 'restauradores_asignados')
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

# --- Personalización principal para ObraDeArte ---
class ObraDeArteAdmin(admin.ModelAdmin):
    # La configuración base se mantiene
    list_filter = ('estado', 'tipo_obra', 'sala', 'periodo')
    search_fields = ('titulo', 'autor')
    inlines = [RestauracionInline]
    change_list_template = "admin/obradearte_changelist.html"
    form = ObraDeArteForm

    # --- Lógica dinámica para la lista de columnas ---
    def get_list_display(self, request):
        # Por defecto, todos ven estas columnas
        display = ['titulo', 'autor', 'estado', 'tipo_obra', 'sala']
        # Si el usuario NO pertenece al grupo 'Restauradores Jefes'...
        if not request.user.groups.filter(name='Restauradores Jefes').exists():
            # ...entonces le añadimos la columna de valoración económica.
            display.append('valoracion_economica')
        return display

    # --- Lógica dinámica para las acciones ---
    def get_actions(self, request):
        actions = super().get_actions(request)
        # Si el usuario pertenece al grupo 'Directores'...
        if request.user.groups.filter(name='Directores').exists():
            # ...le quitamos la acción de enviar a restauración.
            if 'enviar_a_restauracion' in actions:
                del actions['enviar_a_restauracion']
        return actions

    # --- Lógica para las páginas de reportes ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reporte-mantenimiento/', self.admin_site.admin_view(self.reporte_mantenimiento_view), name='reporte_mantenimiento'),
            # AÑADIMOS LA URL PARA EL NUEVO REPORTE
            path('reporte-valoracion/', self.admin_site.admin_view(self.reporte_valoracion_view), name='reporte_valoracion')
        ]
        return custom_urls + urls

    def reporte_mantenimiento_view(self, request):
        obras_necesitadas = []
        for obra in ObraDeArte.objects.all():
            if obra.anios_desde_ultima_restauracion >= 5:
                obras_necesitadas.append(obra)

        context = dict(
           self.admin_site.each_context(request),
           obras_para_mantenimiento=obras_necesitadas,
        )
        return render(request, "admin/reporte_mantenimiento.html", context)

    # AÑADIMOS LA VISTA PARA EL NUEVO REPORTE
    def reporte_valoracion_view(self, request):
        # Usamos aggregate para pedirle a la BD que sume los valores
        calculo = ObraDeArte.objects.aggregate(total_valor=Sum('valoracion_economica'))
        # El resultado viene en un diccionario, ej: {'total_valor': 500000.00}
        total = calculo['total_valor'] or 0 # Si no hay obras, el total es 0

        context = dict(
           self.admin_site.each_context(request),
           total_valor=total,
        )
        return render(request, "admin/reporte_valoracion.html", context)


# --- Personalización del panel para Restauracion ---
class RestauracionAdmin(admin.ModelAdmin):
    form = RestauracionForm
    list_display = ('obra_a_restaurar', 'fecha_inicio', 'fecha_fin')
    autocomplete_fields = ['obra_a_restaurar']
    filter_horizontal = ['restauradores_asignados']

    def save_model(self, request, obj, form, change):
        """
        Método personalizado para guardar un objeto Restauracion desde el admin.
        """
        # Primero, dejamos que Django guarde el objeto Restauracion principal.
        super().save_model(request, obj, form, change)

        # --- LÓGICA PARA EL ESTADO DE LA OBRA (Ya funciona) ---
        if obj.fecha_fin:
            obj.obra_a_restaurar.estado = 'EX'
        else:
            obj.obra_a_restaurar.estado = 'RE'
        obj.obra_a_restaurar.save()

        # --- LÓGICA AÑADIDA PARA EL ESTADO DE LOS RESTAURADORES ---
        # Obtenemos la lista de los restauradores asignados desde el formulario
        restauradores_asignados = form.cleaned_data['restauradores_asignados']

        # Si la restauración terminó, liberamos a los restauradores.
        if obj.fecha_fin:
            restauradores_asignados.update(ocupado=False)
        else:
        # Si la restauración está activa, los marcamos como ocupados.
            restauradores_asignados.update(ocupado=True)

# admin.py
class RestauradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidos', 'email', 'estado_general')
    search_fields = ('nombre', 'apellidos', 'email')
    list_filter = ('estado', 'ocupado')

    @admin.display(description='Disponibilidad')
    def estado_general(self, obj):
        if obj.estado == 'I':
            return 'Inactivo'
        if obj.ocupado:
            return 'En restauración'
        else:
            return 'Libre'

class MuseoColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'pais')
    search_fields = ('nombre', 'ciudad', 'pais')

class CesionAdmin(admin.ModelAdmin):
    list_display = ('obra_cedida', 'museo_destino', 'fecha_inicio', 'fecha_fin')
    autocomplete_fields = ['obra_cedida', 'museo_destino']
    list_filter = ('museo_destino',)
    search_fields = ('obra_cedida__titulo',)

class ExhibicionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin')
    # Usamos filter_horizontal para la selección de obras, que es un ManyToManyField
    filter_horizontal = ('obras_incluidas',)


# --- Registros en el panel de administración ---
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Sala)
admin.site.register(Periodo)
admin.site.register(Estilo)
admin.site.register(Tecnica)
admin.site.register(Material)
admin.site.register(Restaurador, RestauradorAdmin)
admin.site.register(ObraDeArte, ObraDeArteAdmin)
admin.site.register(Restauracion, RestauracionAdmin)
admin.site.register(MuseoColaborador, MuseoColaboradorAdmin)
admin.site.register(Cesion, CesionAdmin)
admin.site.register(Exhibicion, ExhibicionAdmin)