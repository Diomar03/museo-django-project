from django.apps import AppConfig

class CatalogoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogo'

    def ready(self):
        # Esta función se ejecuta cuando la app está lista.
        # Importamos las señales aquí para que se registren correctamente.
        import catalogo.signals 
