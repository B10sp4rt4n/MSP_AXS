#!/bin/bash
# Script de migración automatizado para Neon
# Ejecuta las 3 migraciones en las 3 bases de datos

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 MIGRACIONES AUP - DEPLOY AUTOMATIZADO"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Validar variables de entorno
if [ -z "$DATABASE_URL_CORE" ] || [ -z "$DATABASE_URL_EVENT" ] || [ -z "$DATABASE_URL_GOV" ]; then
    echo "❌ ERROR: Variables de entorno no configuradas"
    echo ""
    echo "Requeridas:"
    echo "  - DATABASE_URL_CORE"
    echo "  - DATABASE_URL_EVENT"
    echo "  - DATABASE_URL_GOV"
    echo ""
    echo "Ejemplo:"
    echo "  export DATABASE_URL_CORE='postgresql://user:pass@host/aup_core'"
    echo "  export DATABASE_URL_EVENT='postgresql://user:pass@host/aup_event'"
    echo "  export DATABASE_URL_GOV='postgresql://user:pass@host/aup_gov'"
    exit 1
fi

echo "✅ Variables de entorno detectadas"
echo ""

# 1. Migración CORE (schema principal)
echo "📊 [1/3] Migrando DATABASE CORE..."
psql "$DATABASE_URL_CORE" -f database/schema_axs.sql
echo "✅ CORE migrado"
echo ""

# 2. Migración EVENT (auditoria)
echo "📊 [2/3] Migrando DATABASE EVENT..."
psql "$DATABASE_URL_EVENT" -f database/migration_event.sql
psql "$DATABASE_URL_EVENT" -f database/migration_03_events_aup.sql
echo "✅ EVENT migrado"
echo ""

# 3. Migración GOV (gobierno)
echo "📊 [3/3] Migrando DATABASE GOV..."
psql "$DATABASE_URL_GOV" -f database/migration_04_gov.sql
psql "$DATABASE_URL_GOV" -f database/migration_05_meta_operativo.sql
echo "✅ GOV migrado"
echo ""

# 4. Bootstrap datos iniciales (solo CORE)
echo "📊 [BOOTSTRAP] Insertando datos sistema..."
psql "$DATABASE_URL_CORE" -f database/bootstrap_aup_sistema.sql
echo "✅ Bootstrap completado"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ MIGRACIONES COMPLETADAS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Próximo paso:"
echo "  1. Verificar tablas: psql \$DATABASE_URL_CORE -c '\\dt'"
echo "  2. Deploy a Railway"
echo "  3. Validar con: curl https://tu-app.railway.app/health"
echo ""
