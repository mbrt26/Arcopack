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

# Detectar el comando Python correcto
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: No se encontró Python en el sistema. Por favor, instala Python o especifica la ruta completa."
    echo "   Puedes editar este script y cambiar PYTHON_CMD con la ruta correcta a tu ejecutable de Python."
    PYTHON_CMD="/usr/bin/python3"  # Intenta con una ruta común
fi

echo "🚀 Iniciando despliegue de ARCOPACK en Google Cloud..."
echo "📌 Usando Python: $PYTHON_CMD"

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

# 7. Verificar que existan todos los archivos estáticos
echo "🔍 Verificando archivos CSS específicos de pedidos..."
mkdir -p static/pedidos/css/
if [ ! -f static/pedidos/css/pedido_form.css ]; then
    echo "Creando archivo CSS faltante para pedidos..."
    echo "/* Estilos para el formulario de pedidos */" > static/pedidos/css/pedido_form.css
    echo "Archivo pedido_form.css creado."
fi

# También verificamos en la carpeta de la aplicación
mkdir -p pedidos/static/pedidos/css/
if [ ! -f pedidos/static/pedidos/css/pedido_form.css ]; then
    echo "Creando archivo CSS faltante en la carpeta de la aplicación pedidos..."
    echo "/* Estilos para el formulario de pedidos */" > pedidos/static/pedidos/css/pedido_form.css
    echo "Archivo pedido_form.css creado en la carpeta de la aplicación."
fi

# 8. Recolectar archivos estáticos manualmente (sin depender de Python)
echo "📁 Preparando archivos estáticos..."
mkdir -p staticfiles/pedidos/css/
cp -f pedidos/static/pedidos/css/pedido_form.css staticfiles/pedidos/css/
echo "✅ Copiados archivos estáticos manualmente."

# Intentar collectstatic solo si Python está disponible
if $PYTHON_CMD -c "print('Python funciona')" 2>/dev/null; then
    echo "📁 Recolectando archivos estáticos con $PYTHON_CMD..."
    export DJANGO_DEBUG=False
    $PYTHON_CMD manage.py collectstatic --clear --noinput
    
    echo "Verificando manifiesto de archivos estáticos..."
    if [ -f staticfiles/staticfiles.json ]; then
        echo "✅ Manifiesto de archivos estáticos generado correctamente."
        grep -q "pedidos/css/pedido_form.css" staticfiles/staticfiles.json && echo "✅ CSS de pedidos encontrado en el manifiesto." || echo "❌ CSS de pedidos NO encontrado en el manifiesto."
    else
        echo "❌ Advertencia: No se generó el manifiesto de archivos estáticos. Continuando de todos modos..."
    fi
    
    # 9. Ejecutar migraciones localmente (opcional)
    echo "🔄 Aplicando migraciones..."
    $PYTHON_CMD manage.py migrate || echo "❌ No se pudieron aplicar migraciones. Continuando de todos modos..."
else
    echo "⚠️ Python no está disponible para collectstatic. Continuando con los archivos copiados manualmente."
fi

# 10. Desplegar aplicación como servicio dedicado
echo "🚀 Desplegando aplicación en App Engine como servicio '$SERVICE_NAME'..."
gcloud app deploy app.yaml --quiet

# 11. Obtener URL de la aplicación
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