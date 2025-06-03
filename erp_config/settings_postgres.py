# Configuración específica para PostgreSQL en Cloud SQL
from .settings import *

# Forzar configuración de PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'arcopackdb',
        'USER': 'arcopackuser',
        'PASSWORD': 'ArcopakDB2025!',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
    }
}

# Asegurar que esté en modo de producción para Cloud SQL
DEBUG = False