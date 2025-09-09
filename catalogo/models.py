from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q 
# --- Tablas de Catálogo (Lookup Tables) ---
# Estas son las listas que el Encargado del Catálogo gestionará.
# El método __str__ es muy importante para que los nombres se muestren
# correctamente en el panel de administración de Django.

class Sala(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Sala")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return self.nombre

class Periodo(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Periodo Histórico")
    def __str__(self):
        return self.nombre

class Estilo(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Estilo Artístico")
    def __str__(self):
        return self.nombre

class Tecnica(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Técnica del Cuadro")
    def __str__(self):
        return self.nombre

class Material(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Material de la Escultura")
    def __str__(self):
        return self.nombre
    class Meta:
        verbose_name_plural = "Materiales"

# --- Entidad Principal: ObraDeArte ---

class ObraDeArte(models.Model):
    # Opciones para campos de elección fija (choices)
    ESTADO_CHOICES = [
        ('EX', 'En exposición'),
        ('RE', 'En restauración'),
        ('CE', 'Cedida'),
        ('BO', 'En Bodega'), # Añadimos un estado por defecto
    ]
    TIPO_CHOICES = [
        ('CU', 'Cuadro'),
        ('ES', 'Escultura'),
    ]

    # Atributos comunes
    titulo = models.CharField(max_length=200, unique=True, verbose_name="Título")
    imagen = models.ImageField(upload_to='obras/', verbose_name="Imagen de la Obra") 
    autor = models.CharField(max_length=200, verbose_name="Autor")
    valoracion_economica = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valoración Económica (S/)")
    fecha_creacion = models.CharField(
        max_length=50, 
        verbose_name="Fecha de Creación", 
        help_text="Introduzca la fecha en formato dd/mm/aaaa o escriba 'Desconocida'."
    )
    fecha_entrada_museo = models.DateField(verbose_name="Fecha de Entrada al Museo")

    # Atributos de estado y tipo
    estado = models.CharField(max_length=2, choices=ESTADO_CHOICES, default='BO', verbose_name="Estado")
    tipo_obra = models.CharField(max_length=2, choices=TIPO_CHOICES, verbose_name="Tipo de Obra")

    # Atributos específicos (pueden ser nulos si no aplican)
    tecnica = models.ManyToManyField(Tecnica, blank=True, verbose_name="Técnica(s) (si es cuadro)")
    material = models.ManyToManyField(Material, blank=True, verbose_name="Material(es) (si es escultura)")

    # Relaciones con las tablas de catálogo (Foreign Keys)
    # on_delete=models.PROTECT evita que se borre un periodo si una obra lo está usando.
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, verbose_name="Periodo")
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, verbose_name="Sala de Ubicación")
    estilo = models.ManyToManyField(Estilo, verbose_name="Estilo(s) Artístico(s)")


    def __str__(self):
        return f"{self.titulo} - {self.autor}"

    # --- MÉTODO PARA MANTENIMIENTO PREVENTIVO ---
    @property
    def anios_desde_ultima_restauracion(self):
        # Buscamos la restauración más reciente para esta obra
        ultima_restauracion = self.restauraciones.order_by('-fecha_fin').first()

        fecha_referencia = None
        if ultima_restauracion and ultima_restauracion.fecha_fin:
            # Si hay una restauración terminada, esa es nuestra fecha de referencia
            fecha_referencia = ultima_restauracion.fecha_fin
        else:
            # Si no, usamos la fecha de entrada al museo
            fecha_referencia = self.fecha_entrada_museo

        # Calculamos la diferencia en días y la convertimos a años
        diferencia = date.today() - fecha_referencia
        return int(diferencia.days / 365.25)
    
    @property
    def fecha_ultima_restauracion_o_entrada(self):
        """
        Devuelve la fecha del fin de la última restauración, 
        o la fecha de entrada si no hay restauraciones.
        """
        ultima_restauracion = self.restauraciones.order_by('-fecha_fin').first()

        if ultima_restauracion and ultima_restauracion.fecha_fin:
            return ultima_restauracion.fecha_fin

        return self.fecha_entrada_museo

    class Meta:
        verbose_name_plural = "Obras de Arte"
# --- FASE 2: MODELOS DE RESTAURACIÓN ---

class Restaurador(models.Model):
    ESTADO_CHOICES = [('A', 'Activo'), ('I', 'Inactivo')]
    nombre = models.CharField(max_length=100, verbose_name="Nombre(s)")
    apellidos = models.CharField(max_length=150, verbose_name="Apellidos")
    email = models.EmailField(max_length=254, unique=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    ESPECIALIDAD_CHOICES = [
        ('CU', 'Cuadros'),
        ('ES', 'Esculturas'),
    ]
    especialidad = models.CharField(max_length=2, choices=ESPECIALIDAD_CHOICES, verbose_name="Especialidad")
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='A', verbose_name="Estado Laboral")
    ocupado = models.BooleanField(default=False, verbose_name="¿Está ocupado en una restauración?")

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"

    class Meta:
        verbose_name = "Restaurador"
        verbose_name_plural = "Restauradores"
        ordering = ['apellidos', 'nombre']


class Restauracion(models.Model):
    obra_a_restaurar = models.ForeignKey(ObraDeArte, on_delete=models.CASCADE, related_name="restauraciones", verbose_name="Obra a Restaurar")
    restauradores_asignados = models.ManyToManyField(Restaurador, verbose_name="Equipo de Restauradores Asignado")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Finalización")
    informe_danos = models.TextField(verbose_name="Informe de Daños / Motivo")
    tipo_restauracion = models.CharField(max_length=200, verbose_name="Tipo de Restauración Realizada")

    def __str__(self):
        return f"Restauración de '{self.obra_a_restaurar.titulo}' - iniciada el {self.fecha_inicio}"

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = "Restauración"
        verbose_name_plural = "Restauraciones"

# --- MODELOS DE DIRECCIÓN Y CESIONES ---

class MuseoColaborador(models.Model):
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del Museo")
    pais = models.CharField(max_length=100, verbose_name="País")
    ciudad = models.CharField(max_length=100, verbose_name="Ciudad")
    enlace_catalogo = models.URLField(max_length=255, verbose_name="Enlace al Catálogo Externo")

    def __str__(self):
        return f"{self.nombre} ({self.ciudad}, {self.pais})"

    class Meta:
        verbose_name = "Museo Colaborador"
        verbose_name_plural = "Museos Colaboradores"
        ordering = ['nombre']

class TelefonoMuseo(models.Model):
    museo = models.ForeignKey(MuseoColaborador, on_delete=models.CASCADE, related_name="telefonos")

    # Creamos una regla de validación
    validador_telefono = RegexValidator(
        regex=r'^\+?[\d\s]+$', # Permite un '+' opcional al inicio, seguido de números y espacios.
        message="El número de teléfono solo puede contener números, espacios y el símbolo '+' al inicio."
    )

    # Aplicamos la regla al campo
    numero = models.CharField(max_length=50, validators=[validador_telefono], verbose_name="Número de Teléfono")

    def __str__(self):
        return self.numero

class EmailMuseo(models.Model):
    # Enlazamos cada email a un museo.
    museo = models.ForeignKey(MuseoColaborador, on_delete=models.CASCADE, related_name="emails")
    email = models.EmailField(max_length=254, verbose_name="Correo Electrónico")

    def __str__(self):
        return self.email

class Cesion(models.Model):
    obras_cedidas = models.ManyToManyField(ObraDeArte, verbose_name="Obras Cedidas")
    museo_destino = models.ForeignKey(MuseoColaborador, on_delete=models.PROTECT, verbose_name="Museo Destino")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio de la Cesión")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin de la Cesión")

    def __str__(self):
        num_obras = self.obras_cedidas.count()
        return f"Cesión de {num_obras} obra(s) a {self.museo_destino.nombre}"

    class Meta:
        verbose_name = "Cesión"
        verbose_name_plural = "Cesiones"
        ordering = ['-fecha_inicio']

class SolicitudCesion(models.Model):
    museo_origen = models.ForeignKey(MuseoColaborador, on_delete=models.PROTECT, verbose_name="Museo al que se solicita")
    fecha_inicio_solicitud = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin_solicitud = models.DateField(verbose_name="Fecha de Fin")

    def __str__(self):
        return f"Solicitud a {self.museo_origen.nombre} ({self.fecha_inicio_solicitud})"

    class Meta:
        verbose_name = "Solicitud de Cesión"
        verbose_name_plural = "Solicitudes de Cesión"
        ordering = ['-fecha_inicio_solicitud']

class ObraSolicitada(models.Model):
    solicitud = models.ForeignKey(SolicitudCesion, on_delete=models.CASCADE, related_name="obras_solicitadas")
    nombre_obra = models.CharField(max_length=255, verbose_name="Nombre de la Obra")

    def __str__(self):
        return self.nombre_obra

class Exhibicion(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Exhibición")
    imagen = models.ImageField(upload_to='exhibiciones/', verbose_name="Imagen para el Carrusel")
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    
    # Relación Muchos-a-Muchos con las obras de arte
    obras_incluidas = models.ManyToManyField(ObraDeArte, verbose_name="Obras Incluidas en la Exhibición", blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Exhibición"
        verbose_name_plural = "Exhibiciones"
        ordering = ['-fecha_inicio']

