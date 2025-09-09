from django import forms
from django.contrib.auth.models import User, Group
from .models import ObraDeArte, Restauracion, Exhibicion, Cesion


# --- Formulario para la validación de Roles de Usuario ---
class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean(self):
        """
        Este método se ejecuta para validar los datos del formulario antes de guardarlos.
        """
        cleaned_data = super().clean()
        
        groups = cleaned_data.get("groups")
        is_active = cleaned_data.get("is_active")

        main_roles = ['Directores', 'Encargados de Catálogo', 'Restauradores Jefes']

        if is_active and groups and groups.filter(name__in=main_roles).exists():
            for group in groups:
                if group.name in main_roles:
                    existing_user = User.objects.filter(groups=group, is_active=True).exclude(pk=self.instance.pk).first()
                    
                    if existing_user:
                        raise forms.ValidationError(
                            f"Ya existe un usuario activo ('{existing_user.username}') para el rol '{group.name}'. "
                            f"Por favor, desactiva o cambia el rol del usuario existente antes de activar este."
                        )
        
        return cleaned_data


# --- Formulario para la validación de Obras de Arte ---
class ObraDeArteForm(forms.ModelForm):
    class Meta:
        model = ObraDeArte
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        tipo_obra = cleaned_data.get("tipo_obra")
        tecnicas_seleccionadas = cleaned_data.get("tecnica")
        materiales_seleccionados = cleaned_data.get("material")

        # Regla 1: Si es un Cuadro, no puede tener Materiales.
        if tipo_obra == 'CU' and materiales_seleccionados.exists():
            raise forms.ValidationError(
                "Un Cuadro no puede tener Materiales. Por favor, asegúrate de que la lista de materiales esté vacía."
            )

        # Regla 2: Si es una Escultura, no puede tener Técnicas.
        if tipo_obra == 'ES' and tecnicas_seleccionadas.exists():
            raise forms.ValidationError(
                "Una Escultura no puede tener Técnicas. Por favor, asegúrate de que la lista de técnicas esté vacía."
            )

        # --- NUEVA VALIDACIÓN ---
        # Regla 3: Si es un Cuadro, DEBE tener al menos una Técnica.
        if tipo_obra == 'CU' and not tecnicas_seleccionadas.exists():
            raise forms.ValidationError(
                "Un Cuadro debe tener al menos una técnica seleccionada."
            )

        # Regla 4: Si es una Escultura, DEBE tener al menos un Material.
        if tipo_obra == 'ES' and not materiales_seleccionados.exists():
            raise forms.ValidationError(
                "Una Escultura debe tener al menos un material seleccionado."
            )

        return cleaned_data

class RestauracionForm(forms.ModelForm):
    class Meta:
        model = Restauracion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        obra = cleaned_data.get("obra_a_restaurar")
        restauradores = cleaned_data.get("restauradores_asignados")

        # Si los campos principales no están, dejamos que la validación por defecto actúe
        if not obra:
            return cleaned_data

        # Verificamos primero el estado de la obra
        if not self.instance.pk and obra.estado in ['RE', 'CE']:
            raise forms.ValidationError(
                f"No se puede iniciar una restauración para '{obra.titulo}' porque su estado actual es '{obra.get_estado_display()}'."
            )

        # --- Lógica de recolección de errores ---
        lista_de_errores = []

        if restauradores:
            for restaurador in restauradores:
                # Verificamos si está ocupado
                if restaurador.ocupado:
                    # Si estamos editando, puede que ya estuviera asignado a ESTA restauración, eso está bien.
                    if not self.instance.pk or restaurador not in self.instance.restauradores_asignados.all():
                        lista_de_errores.append(
                            forms.ValidationError(f"El restaurador '{restaurador}' ya se encuentra ocupado.", code='ocupado')
                        )

                # Verificamos si su especialidad coincide con el tipo de obra
                if restaurador.especialidad != obra.tipo_obra:
                    lista_de_errores.append(
                        forms.ValidationError(f"La especialidad de '{restaurador}' ({restaurador.get_especialidad_display()}) no coincide con el tipo de obra ({obra.get_tipo_obra_display()}).", code='especialidad')
                    )

        # Si nuestra lista de errores tiene algo, lanzamos la excepción con todos los mensajes
        if lista_de_errores:
            raise forms.ValidationError(lista_de_errores)

        return cleaned_data
    
class ExhibicionForm(forms.ModelForm):
    class Meta:
        model = Exhibicion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        obras = cleaned_data.get('obras_incluidas')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Creamos una lista para guardar todos los mensajes de error
        errores_de_conflicto = []

        # 1. Validación de mínimo 3 obras
        if obras and len(obras) < 3:
            raise forms.ValidationError("Una exhibición debe tener al menos 3 obras de arte seleccionadas.")

        # 2. Validación de solapamiento de fechas
        if obras and fecha_inicio and fecha_fin:
            for obra in obras:
                otras_exhibiciones = Exhibicion.objects.filter(obras_incluidas=obra).exclude(pk=self.instance.pk)
                for otra_exhibicion in otras_exhibiciones:
                    if max(fecha_inicio, otra_exhibicion.fecha_inicio) < min(fecha_fin, otra_exhibicion.fecha_fin):
                        # En lugar de lanzar el error, lo añadimos a nuestra lista
                        mensaje = (f"La obra '{obra.titulo}' ya está en la exhibición '{otra_exhibicion.nombre}' "
                                f"durante estas fechas (del {otra_exhibicion.fecha_inicio.strftime('%d/%m/%Y')} "
                                f"al {otra_exhibicion.fecha_fin.strftime('%d/%m/%Y')}).")
                        errores_de_conflicto.append(mensaje)

        # Al final, si hemos encontrado algún error en la lista, lanzamos la excepción
        if errores_de_conflicto:
            raise forms.ValidationError(errores_de_conflicto)

        return cleaned_data
    

class CesionForm(forms.ModelForm):
    class Meta:
        model = Cesion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        obras_seleccionadas = cleaned_data.get('obras_cedidas')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Si los campos principales no están, Django ya se quejará.
        if not obras_seleccionadas or not fecha_inicio or not fecha_fin:
            return cleaned_data

        lista_de_errores = []

        for obra in obras_seleccionadas:
            # 1. Verificación: La obra no puede estar en restauración.
            if obra.estado == 'RE':
                lista_de_errores.append(
                    f"La obra '{obra.titulo}' no puede ser cedida porque está en restauración."
                )

            # 2. Verificación: Las fechas no pueden solaparse.
            cesiones_existentes = Cesion.objects.filter(obras_cedidas=obra).exclude(pk=self.instance.pk)
            for cesion_existente in cesiones_existentes:
                if max(fecha_inicio, cesion_existente.fecha_inicio) < min(fecha_fin, cesion_existente.fecha_fin):
                    mensaje = (f"Las fechas para la obra '{obra.titulo}' se solapan con una cesión existente.")
                    if mensaje not in lista_de_errores:
                        lista_de_errores.append(mensaje)

        # Si hemos recolectado algún error, lo lanzamos.
        if lista_de_errores:
            raise forms.ValidationError(lista_de_errores)

        return cleaned_data