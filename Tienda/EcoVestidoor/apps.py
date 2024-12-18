from django.apps import AppConfig


class EcovestidoorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'EcoVestidoor'

    def ready(self):
        from . import signals  # Importación dentro del método read
