#!/bin/bash
# Script para configurar el tenant y usuarios del piloto
# Ejecutar DESPUÉS del deploy exitoso

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 SETUP PILOTO - Crear Tenant + Usuarios"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Configuración
if [ -z "$API_URL" ]; then
    echo "❌ ERROR: Variable API_URL no definida"
    echo "Ejemplo: export API_URL='https://tu-app.railway.app'"
    exit 1
fi

if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ ERROR: Credenciales de admin no definidas"
    echo "Requeridas:"
    echo "  export ADMIN_EMAIL='admin@msp.com'"
    echo "  export ADMIN_PASSWORD='tu-password-seguro'"
    exit 1
fi

echo "API: $API_URL"
echo "Admin: $ADMIN_EMAIL"
echo ""

# 1. Login como admin
echo "📊 [1/4] Autenticando admin..."
TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Error en login - verificar credenciales"
    exit 1
fi

echo "✅ Token obtenido"
echo ""

# 2. Crear tenant piloto
echo "📊 [2/4] Creando tenant piloto..."
TENANT_RESPONSE=$(curl -s -X POST "$API_URL/condominios" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "nombre": "Condominio Piloto AUP",
        "direccion": "Calle Prueba 123",
        "telefono": "+52 555 1234567",
        "tenant_id": "condo-piloto-001"
    }')

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.id // .tenant_id // "condo-piloto-001"')
echo "✅ Tenant creado: $TENANT_ID"
echo ""

# 3. Crear usuarios del piloto
echo "📊 [3/4] Creando usuarios piloto..."

# Array de usuarios (ajustar según necesidad)
declare -a USUARIOS=(
    "admin-piloto:admin.piloto@test.com:AdminPiloto2026:ADMIN"
    "caseta-piloto:caseta.piloto@test.com:CasetaPiloto2026:CASETA"
    "residente1:residente1@test.com:Residente2026:RESIDENTE"
    "residente2:residente2@test.com:Residente2026:RESIDENTE"
    "residente3:residente3@test.com:Residente2026:RESIDENTE"
    "residente4:residente4@test.com:Residente2026:RESIDENTE"
    "residente5:residente5@test.com:Residente2026:RESIDENTE"
    "residente6:residente6@test.com:Residente2026:RESIDENTE"
)

CREATED_COUNT=0
for USER_DATA in "${USUARIOS[@]}"; do
    IFS=':' read -r NOMBRE EMAIL PASSWORD ROL <<< "$USER_DATA"
    
    echo "  → Creando: $EMAIL ($ROL)"
    
    USER_RESPONSE=$(curl -s -X POST "$API_URL/usuarios" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"nombre\": \"$NOMBRE\",
            \"email\": \"$EMAIL\",
            \"password\": \"$PASSWORD\",
            \"rol\": \"$ROL\",
            \"condominio_id\": \"$TENANT_ID\"
        }")
    
    if echo "$USER_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
        ((CREATED_COUNT++))
    else
        echo "    ⚠️  Posible error en creación"
    fi
done

echo "✅ $CREATED_COUNT usuarios creados"
echo ""

# 4. Configurar scopes
echo "📊 [4/4] Configurando scopes multi-tenant..."
echo "⚠️  NOTA: Scopes deben configurarse manualmente en DB si no hay endpoint"
echo ""
echo "SQL para ejecutar en DATABASE_URL_CORE:"
echo ""
echo "INSERT INTO scopes (usuario_id, condominio_id, nivel_acceso)"
echo "SELECT u.id, '$TENANT_ID', 'LECTURA_ESCRITURA'"
echo "FROM usuarios u"
echo "WHERE u.email LIKE '%@test.com';"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ SETUP PILOTO COMPLETADO"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 RESUMEN:"
echo "  Tenant: $TENANT_ID"
echo "  Usuarios: $CREATED_COUNT"
echo "  API: $API_URL"
echo ""
echo "🎯 CREDENCIALES DE PRUEBA:"
echo ""
for USER_DATA in "${USUARIOS[@]}"; do
    IFS=':' read -r NOMBRE EMAIL PASSWORD ROL <<< "$USER_DATA"
    echo "  $ROL:"
    echo "    Email: $EMAIL"
    echo "    Pass:  $PASSWORD"
    echo ""
done
echo ""
echo "🔍 VALIDAR PILOTO:"
echo "  1. Login: curl -X POST $API_URL/auth/login -d '{\"email\":\"residente1@test.com\",\"password\":\"Residente2026\"}'"
echo "  2. Test RLS: curl $API_URL/visitas/mis-visitas/$TENANT_ID -H \"Authorization: Bearer \$TOKEN\""
echo "  3. Revisar logs: Buscar '✅ RLS activado: tenant=$TENANT_ID'"
echo ""
echo "⏱️  PILOTO 72 HORAS - Inicio: $(date)"
echo ""
