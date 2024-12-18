from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth import get_user_model  # Lazy loading del modelo
import logging

# Configurar el logger
logger = logging.getLogger(__name__)

# Obtener el modelo de usuario de forma segura
User = get_user_model()

@receiver(user_logged_in)
def log_usuario_ingresado(sender, request, user, **kwargs):
    if isinstance(user, User):
        logger.info(f"Usuario {user.username} ha iniciado sesión.")
        print(f"Usuario {user.username} ha iniciado sesión.")

@receiver(user_logged_out)
def log_usuario_cerrado(sender, request, user, **kwargs):
    if isinstance(user, User):
        logger.info(f"Usuario {user.username} ha cerrado sesión.")
        print(f"Usuario {user.username} ha cerrado sesión.")
