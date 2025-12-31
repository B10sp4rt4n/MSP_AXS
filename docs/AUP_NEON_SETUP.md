# PREPARACIÓN DE BASES NEON - AUP

**Fecha:** 2025-12-29  
**Objetivo:** Definir estructura de bases de datos separadas para dominios AUP.

---

## BASES REQUERIDAS

### 1. `aup_core` - Identidad y Alcance

**Propósito:**  
Declarar existencia de identidades (usuarios), tenants (condominios), alcances (scopes) y entidades de negocio (visitas, evidencias).

**Responsabilidad:**
- AUP_IDENTITY (usuarios)
- AUP_TENANT (MSPs, condominios)
- AUP_SCOPE (alcances de usuarios en tenants)
- Entidades operativas (visitas, evidencias, casetas)

**Tablas esperadas:**
- `usuarios_exo`
- `msps_exo`
- `condominios_exo`
- `user_tenant_scope`
- `visitas`
- `evidencias`
- `casetas`

### 2. `aup_event` - Verdad Histórica

**Propósito:**  
Registrar hechos inmutables del sistema con identidad, alcance y resultado verificables.

**Responsabilidad:**
- AUP_EVENT (registro universal de hechos)
- Append-only (solo INSERT, nunca UPDATE/DELETE)
- Hash de inmutabilidad

**Tablas esperadas:**
- `events_aup`

**Axiomas críticos:**
- Si no hay evento, no ocurrió para el sistema
- Si hash cambia, hay manipulación detectable
- Estado del sistema se puede reconstruir desde eventos

### 3. `aup_gov` - Poder Explícito

**Propósito:**  
Declarar quién tiene poder, sobre qué, bajo qué límites.

**Responsabilidad:**
- AUP_AUTHORITY (actores con potestad)
- AUP_POLICY (reglas declarativas)
- AUP_DELEGATION (transferencia de poder)

**Tablas esperadas:**
- `authorities_gov`
- `policies_gov`
- `delegations_gov`

**Axiomas críticos:**
- Gobierno precede operación
- Sin política asignada → denegado (default deny)
- Si AUP_GOV falla → operación denegada

---

## VARIABLES DE ENTORNO

### Archivo: `.env`

```bash
# ═══════════════════════════════════════════════════════════════════════════
# AUP: Bases de Datos Separadas por Dominio
# ═══════════════════════════════════════════════════════════════════════════

# AUP_CORE: Identidad, Alcance, Negocio
DATABASE_CORE_URL=postgresql://USER:PASSWORD@HOST/aup_core

# AUP_EVENT: Verdad Histórica (Append-Only)
DATABASE_EVENT_URL=postgresql://USER:PASSWORD@HOST/aup_event

# AUP_GOV: Poder Explícito (Políticas, Autoridades)
DATABASE_GOV_URL=postgresql://USER:PASSWORD@HOST/aup_gov

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTANTE: Reemplazar USER, PASSWORD, HOST con credenciales reales de Neon
# ═══════════════════════════════════════════════════════════════════════════
```

### Fallback local (desarrollo)

Si las variables no están definidas, el sistema usa SQLite local:
- `sqlite:///./axs_core.db`
- `sqlite:///./axs_event.db`
- `sqlite:///./axs_gov.db`

---

## CHECKLIST DE CREACIÓN EN NEON

### Paso 1: Crear proyectos/bases

```bash
□ Crear base: aup_core
□ Crear base: aup_event
□ Crear base: aup_gov
□ Obtener URLs de conexión
```

### Paso 2: Agregar URLs a `.env`

```bash
□ Copiar URL de aup_core → DATABASE_CORE_URL
□ Copiar URL de aup_event → DATABASE_EVENT_URL
□ Copiar URL de aup_gov → DATABASE_GOV_URL
```

### Paso 3: Ejecutar migraciones

**3.1 — Migración CORE**

```bash
# Ejecutar en aup_core:
psql $DATABASE_CORE_URL < database/schema_axs.sql
psql $DATABASE_CORE_URL < database/migration_03_events_aup.sql  # Solo tablas CORE
```

**3.2 — Migración EVENT**

```bash
# Crear manualmente la tabla events_aup en aup_event
# (Ver estructura en backend/db/event/models.py)
```

Archivo: `database/migration_event.sql`

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- AUP_EVENT: Tabla de Verdad Histórica
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS events_aup (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100) NOT NULL,
    identity_id VARCHAR(50) NOT NULL,
    session_hash VARCHAR(16) NOT NULL,
    scope_id VARCHAR(50),
    tenant_id VARCHAR(50) NOT NULL,
    entidad VARCHAR(50) NOT NULL,
    entidad_id VARCHAR(100) NOT NULL,
    accion VARCHAR(50) NOT NULL,
    resultado VARCHAR(50) NOT NULL,
    motivo TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    hash_evento VARCHAR(64) NOT NULL UNIQUE,
    metadata_json JSONB
);

-- Índices para queries comunes
CREATE INDEX idx_events_identity_tenant ON events_aup(identity_id, tenant_id, timestamp);
CREATE INDEX idx_events_entidad ON events_aup(entidad, entidad_id, timestamp);
CREATE INDEX idx_events_resultado ON events_aup(resultado, timestamp);
CREATE INDEX idx_events_tipo ON events_aup(tipo_evento, timestamp);

COMMENT ON TABLE events_aup IS 'AUP_EVENT: Registro inmutable de hechos estructurales';
```

**3.3 — Migración GOV**

```bash
# Ejecutar en aup_gov:
psql $DATABASE_GOV_URL < database/migration_04_gov.sql
```

### Paso 4: Verificar tablas

```bash
# Verificar CORE
psql $DATABASE_CORE_URL -c "\dt"

# Verificar EVENT
psql $DATABASE_EVENT_URL -c "\dt"

# Verificar GOV
psql $DATABASE_GOV_URL -c "\dt"
```

### Paso 5: Ejecutar seeds

```bash
# Crear scopes iniciales (CORE)
python scripts/migrate_create_scopes.py

# Bootstrap de gobierno (CORE + GOV)
python scripts/seed_gov_bootstrap.py

# Planes comerciales (GOV)
python scripts/seed_planes_comerciales.py
```

---

## MIGRACIONES POR DOMINIO

### `database/migration_core.sql`
Contiene:
- Tablas de identidad (`usuarios_exo`, `msps_exo`, `condominios_exo`)
- Tabla de alcance (`user_tenant_scope`)
- Tablas de negocio (`visitas`, `evidencias`, `casetas`)

### `database/migration_event.sql`
Contiene:
- Tabla de eventos (`events_aup`)
- Índices para consultas temporales
- Comentarios de axiomas

### `database/migration_gov.sql`
Contiene:
- Tabla de autoridades (`authorities_gov`)
- Tabla de políticas (`policies_gov`)
- Tabla de delegaciones (`delegations_gov`)

---

## VALIDACIÓN POST-MIGRACIÓN

### Script: `scripts/verify_migration.py`

```python
#!/usr/bin/env python3
"""
Verifica que las 3 bases AUP tienen las tablas correctas.
"""

import os
from sqlalchemy import inspect
from backend.db.core import engine_core
from backend.db.event import engine_event
from backend.db.gov import engine_gov


def verificar_core():
    """Verifica tablas en AUP_CORE"""
    inspector = inspect(engine_core)
    tablas = inspector.get_table_names()
    
    esperadas = [
        "usuarios_exo",
        "msps_exo",
        "condominios_exo",
        "user_tenant_scope",
        "visitas",
        "evidencias",
        "casetas"
    ]
    
    print("\n[AUP_CORE]")
    for tabla in esperadas:
        status = "✓" if tabla in tablas else "✗"
        print(f"  {status} {tabla}")
    
    return all(t in tablas for t in esperadas)


def verificar_event():
    """Verifica tablas en AUP_EVENT"""
    inspector = inspect(engine_event)
    tablas = inspector.get_table_names()
    
    print("\n[AUP_EVENT]")
    status = "✓" if "events_aup" in tablas else "✗"
    print(f"  {status} events_aup")
    
    return "events_aup" in tablas


def verificar_gov():
    """Verifica tablas en AUP_GOV"""
    inspector = inspect(engine_gov)
    tablas = inspector.get_table_names()
    
    esperadas = [
        "authorities_gov",
        "policies_gov",
        "delegations_gov"
    ]
    
    print("\n[AUP_GOV]")
    for tabla in esperadas:
        status = "✓" if tabla in tablas else "✗"
        print(f"  {status} {tabla}")
    
    return all(t in tablas for t in esperadas)


def main():
    print("═" * 60)
    print("VERIFICACIÓN DE MIGRACIONES AUP")
    print("═" * 60)
    
    core_ok = verificar_core()
    event_ok = verificar_event()
    gov_ok = verificar_gov()
    
    print("\n" + "═" * 60)
    
    if core_ok and event_ok and gov_ok:
        print("✅ TODAS LAS BASES ESTÁN CORRECTAS")
        print("═" * 60)
        return 0
    else:
        print("❌ FALTAN TABLAS - Ejecutar migraciones faltantes")
        print("═" * 60)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

---

## SEGURIDAD Y AISLAMIENTO

### Principios de separación:

1. **Aislamiento físico:**
   - Cada base vive en su propio namespace
   - No hay foreign keys entre bases
   - Relaciones solo por IDs (UUID)

2. **Axioma de fallo:**
   - Si EVENT cae → el sistema registra en memoria temporal
   - Si GOV cae → **deny by default** (operaciones bloqueadas)
   - Si CORE cae → sistema no puede operar

3. **Backups independientes:**
   - CORE: backup crítico (identidades)
   - EVENT: append-only, nunca se borra
   - GOV: backup de políticas (recuperable desde seed)

---

## ESTADO ACTUAL

| Componente                  | Estado       | Notas                                   |
|-----------------------------|--------------|----------------------------------------|
| Modelos separados           | ✅ COMPLETO  | `backend/db/{core,event,gov}/models.py`|
| Engines separados           | ✅ COMPLETO  | Cada dominio tiene su engine           |
| SessionLocal separados      | ✅ COMPLETO  | `SessionLocal_{CORE,EVENT,GOV}`        |
| Variables entorno definidas | ✅ COMPLETO  | En `engine.py` de cada dominio         |
| Migraciones SQL             | 🔜 PENDIENTE | Crear `migration_event.sql`            |
| Bases en Neon               | 🔜 TU TAREA  | Crear 3 proyectos en Neon              |
| Script verificación         | 🔜 PENDIENTE | Crear `verify_migration.py`            |

---

## PRÓXIMO PASO INMEDIATO

**No continúes el desarrollo sin ejecutar esto:**

1. Crear las 3 bases en Neon
2. Agregar URLs al `.env`
3. Ejecutar migraciones
4. Ejecutar `verify_migration.py`
5. Ver todas las tablas en verde

**Tiempo estimado:** 30 minutos reales.

---

**Declaración AUP:**  
Una arquitectura sin su memoria correctamente declarada  
es una promesa sin fundamento.  
Hasta que las bases no existan y las tablas no estén ahí,  
el sistema AUP está en estado de diseño, no de existencia.
