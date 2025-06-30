from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Restauracion, Restaurador

@receiver(m2m_changed, sender=Restauracion.restauradores_asignados.through)
def actualizar_estado_restauradores(sender, instance, action, **kwargs):
    """
    Esta función se activa cada vez que la relación entre una Restauración
    y sus Restauradores cambia.
    """
    # Solo nos interesa actuar después de que se hayan añadido o quitado restauradores.
    if action in ["post_add", "post_remove", "post_clear"]:
        # Recalculamos el estado de CADA restaurador que ha estado en esta restauración.
        for restaurador in instance.restauradores_asignados.all():
            # Si el restaurador está en CUALQUIER restauración SIN fecha de fin, está ocupado.
            if restaurador.restauracion_set.filter(fecha_fin__isnull=True).exists():
                restaurador.ocupado = True
            else:
                restaurador.ocupado = False
            restaurador.save()

        # Si la acción fue quitar o limpiar, también debemos actualizar a los que se quitaron.
        if action in ["post_remove", "post_clear"]:
            pk_set = kwargs.get('pk_set')
            for restaurador in Restaurador.objects.filter(pk__in=pk_set):
                 if not restaurador.restauracion_set.filter(fecha_fin__isnull=True).exists():
                    restaurador.ocupado = False
                    restaurador.save()