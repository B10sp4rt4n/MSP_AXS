#!/bin/bash
# Script de validación post-deploy
# Verifica que el sistema esté funcionando correctamente

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🔍 VALIDACIÓN POST-DEPLOY - AUP SYSTEM"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Configuración
if [ -z "$API_URL" ]; then
    echo "⚠️  Variable API_URL no definida, usando localhost"
    API_URL="http://localhost:8000"
fi

echo "Target: $API_URL"
echo ""

# Test 1: Health Check
echo "📊 [TEST 1/5] Health Check..."
HEALTH=$(curl -s "$API_URL/health" || echo "FAIL")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health check OK"
else
    echo "❌ Health check FAILED"
    echo "Response: $HEALTH"
    exit 1
fi
echo ""

# Test 2: Login endpoint (debe estar disponible)
echo "📊 [TEST 2/5] Login endpoint disponible..."
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/auth/login" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong"}' || echo "000")

if [ "$LOGIN_STATUS" = "401" ] || [ "$LOGIN_STATUS" = "422" ]; then
    echo "✅ Login endpoint respondiendo (status: $LOGIN_STATUS)"
else
    echo "❌ Login endpoint no responde correctamente (status: $LOGIN_STATUS)"
    exit 1
fi
echo ""

# Test 3: Endpoint protegido sin token (debe dar 401)
echo "📊 [TEST 3/5] Protección JWT activa..."
PROTECTED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/visitas/mis-visitas/test-tenant" || echo "000")

if [ "$PROTECTED_STATUS" = "401" ] || [ "$PROTECTED_STATUS" = "403" ]; then
    echo "✅ JWT protección activa (status: $PROTECTED_STATUS)"
else
    echo "⚠️  Respuesta inesperada en endpoint protegido (status: $PROTECTED_STATUS)"
fi
echo ""

# Test 4: CORS headers
echo "📊 [TEST 4/5] CORS configurado..."
CORS_HEADERS=$(curl -s -I "$API_URL/health" | grep -i "access-control" || echo "")
if [ -n "$CORS_HEADERS" ]; then
    echo "✅ CORS headers presentes"
else
    echo "⚠️  No se detectaron headers CORS (puede ser intencional)"
fi
echo ""

# Test 5: Docs disponibles
echo "📊 [TEST 5/5] Documentación API..."
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs" || echo "000")
if [ "$DOCS_STATUS" = "200" ]; then
    echo "✅ Swagger docs disponibles en $API_URL/docs"
else
    echo "⚠️  Docs no accesibles (status: $DOCS_STATUS)"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ VALIDACIÓN BÁSICA COMPLETADA"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🎯 PRÓXIMOS PASOS MANUALES:"
echo ""
echo "1. Login con usuario real:"
echo "   curl -X POST $API_URL/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\":\"admin@test.com\",\"password\":\"tu-password\"}'"
echo ""
echo "2. Verificar RLS con token:"
echo "   TOKEN=\$(curl -X POST $API_URL/auth/login ... | jq -r '.access_token')"
echo "   curl $API_URL/visitas/mis-visitas/tenant-test \\"
echo "     -H \"Authorization: Bearer \$TOKEN\""
echo ""
echo "3. Revisar logs en Railway:"
echo "   - Buscar: '✅ RLS activado'"
echo "   - Buscar: 'ACCESO DENEGADO'"
echo "   - Verificar: 0 errores 500"
echo ""
