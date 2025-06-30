from django import forms
from django.contrib.auth.models import User, Group
from .models import ObraDeArte, Restauracion

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
        """
        Valida que los cuadros no tengan material y las esculturas no tengan técnica.
        """
        cleaned_data = super().clean()
        tipo_obra = cleaned_data.get("tipo_obra")
        tecnica = cleaned_data.get("tecnica")
        material = cleaned_data.get("material")

        # Regla 1: Si es un Cuadro, no puede tener un Material.
        if tipo_obra == 'CU' and material:
            raise forms.ValidationError(
                "Un Cuadro no puede tener un Material de escultura. Por favor, deja el campo 'Material' vacío."
            )

        # Regla 2: Si es una Escultura, no puede tener una Técnica.
        if tipo_obra == 'ES' and tecnica:
            raise forms.ValidationError(
                "Una Escultura no puede tener una Técnica de cuadro. Por favor, deja el campo 'Técnica' vacío."
            )
        
        return cleaned_data

class RestauracionForm(forms.ModelForm):
    class Meta:
        model = Restauracion
        fields = '__all__'

    def clean_obra_a_restaurar(self):
        obra = self.cleaned_data.get('obra_a_restaurar')
        # 'self.instance.pk' nos ayuda a saber si estamos creando un nuevo objeto o editando uno existente.
        # La validación solo aplica al crear una nueva restauración.
        if not self.instance.pk and obra and obra.estado in ['RE', 'CE']:
            raise forms.ValidationError(
                f"No se puede iniciar una nueva restauración para '{obra.titulo}' porque su estado actual es '{obra.get_estado_display()}'."
            )
        return obra