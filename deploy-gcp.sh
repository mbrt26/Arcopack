#!/bin/bash

# Script de despliegue para ARCOPACK en Google Cloud Platform
# Asegúrate de haber habilitado la facturación en tu proyecto antes de ejecutar

set -e  # Salir si cualquier comando falla

PROJECT_ID="appsindunnova"
REGION="southamerica-east1"
DB_INSTANCE="arcopack-db"
DB_NAME="arcopackdb"
DB_USER="arcopackuser"
DB_PASSWORD="ArcopakDB2025!"
SERVICE_NAME="arcopack"

echo "🚀 Iniciando despliegue de ARCOPACK en Google Cloud..."

# 1. Configurar proyecto
echo "📋 Configurando proyecto..."
gcloud config set project $PROJECT_ID

# 2. Habilitar APIs necesarias
echo "🔧 Habilitando APIs necesarias..."
gcloud services enable appengine.googleapis.com sqladmin.googleapis.com cloudbuild.googleapis.com

# 3. Crear instancia de Cloud SQL (solo si no existe)
echo "🗄️ Verificando instancia de Cloud SQL..."
if ! gcloud sql instances describe $DB_INSTANCE --quiet 2>/dev/null; then
    echo "Creando nueva instancia de Cloud SQL..."
    gcloud sql instances create $DB_INSTANCE \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04
else
    echo "Instancia de Cloud SQL ya existe."
fi

# 4. Crear base de datos (solo si no existe)
echo "📊 Verificando base de datos..."
if ! gcloud sql databases describe $DB_NAME --instance=$DB_INSTANCE --quiet 2>/dev/null; then
    echo "Creando base de datos..."
    gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE
else
    echo "Base de datos ya existe."
fi

# 5. Crear usuario de base de datos (solo si no existe)
echo "👤 Verificando usuario de base de datos..."
if ! gcloud sql users describe $DB_USER --instance=$DB_INSTANCE --quiet 2>/dev/null; then
    echo "Creando usuario de base de datos..."
    gcloud sql users create $DB_USER \
        --instance=$DB_INSTANCE \
        --password=$DB_PASSWORD
else
    echo "Usuario de base de datos ya existe."
fi

# 6. Inicializar App Engine (solo si no existe)
echo "🏗️ Verificando App Engine..."
if ! gcloud app describe --quiet 2>/dev/null; then
    echo "Inicializando App Engine..."
    gcloud app create --region=$REGION
else
    echo "App Engine ya está inicializado."
fi

# 7. Recolectar archivos estáticos
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# 8. Ejecutar migraciones localmente (opcional)
echo "🔄 Aplicando migraciones..."
python manage.py migrate

# 9. Desplegar aplicación como servicio dedicado
echo "🚀 Desplegando aplicación en App Engine como servicio '$SERVICE_NAME'..."
gcloud app deploy app.yaml --quiet

# 10. Obtener URL de la aplicación
echo "✅ Despliegue completado!"
echo "🌐 URLs de la aplicación:"
echo "   Servicio principal: https://$SERVICE_NAME-dot-$PROJECT_ID.rj.r.appspot.com"
echo "   URL alternativa: https://$PROJECT_ID.rj.r.appspot.com (default)"

echo ""
echo "📝 Próximos pasos:"
echo "1. Configurar el dominio personalizado si es necesario"
echo "2. Configurar Secret Manager para credenciales sensibles"
echo "3. Configurar respaldos automáticos de la base de datos"
echo "4. Revisar y ajustar configuraciones de escalado"
echo "5. Verificar que el servicio '$SERVICE_NAME' funcione correctamente"