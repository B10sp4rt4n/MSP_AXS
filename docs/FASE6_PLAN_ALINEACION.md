# FASE 6: PLAN DE ALINEACIÓN DE IMPLEMENTACIÓN

**Versión:** 1.0.0  
**Fecha:** 2026-01-01  
**Tipo:** Plan Operativo de Migración  
**Estado:** Activo

---

## DECLARACIÓN DE PROPÓSITO

Este documento define las acciones concretas para que el código backend
ejecute EXACTAMENTE lo que la arquitectura AUP ya define.

**No es:**
- Un rediseño
- Una optimización
- Una propuesta de mejora

**Es:**
- Un plan de obediencia arquitectónica
- Una guía de migración controlada
- Un conjunto de criterios de aceptación

---

## 1. DECLARACIÓN DE PROHIBICIÓN FORMAL

### 1.1 Estado de `verificar_rol()`

| Atributo | Valor |
|----------|-------|
| **Estado** | DEPRECADO |
| **Fecha de deprecación** | 2026-01-01 |
| **Fecha de muerte** | 2026-04-01 |
| **Razón** | Viola FASE 1 (identity_label) |
| **Reemplazo** | `validar_scope()` + `puede_ejecutar_accion()` |

### 1.2 Regla de Código

```
REGLA ROL-001: Prohibición de uso de rol para autorización

APLICA A:
  - Todo código nuevo
  - Todo código modificado
  - Todo código en revisión

PROHIBIDO:
  - verificar_rol(usuario, [...])
  - usuario.rol == "..."
  - usuario.rol in [...]
  - if usuario.rol:
  - cualquier condicional basado en usuario.rol

PERMITIDO (solo lectura/metadata):
  - logging: logger.info(f"usuario.rol={usuario.rol}")
  - eventos: metadata={"identity_label": usuario.rol}
  - UI hints: response.display_role = usuario.rol

EXCEPCIÓN TEMPORAL:
  - Código legacy no modificado (hasta fecha de muerte)
```

### 1.3 Marcado en Código

**Inmediato:** Agregar docstring de deprecación a `verificar_rol()`:

```python
def verificar_rol(usuario, roles_permitidos: list[str]):
    """
    ⛔ DEPRECADO — NO USAR EN CÓDIGO NUEVO
    
    Fecha de muerte: 2026-04-01
    
    Reemplazar por:
        from backend.core.scope.validator import validar_scope
        validar_scope(db, usuario, tenant_id, AccessLevel.REQUERIDO)
    
    Documentación: docs/ESPECIFICACION_CAMPO_ROL.md
    
    Este método viola FASE 1: rol es metadata, no autorización.
    """
    # ... código existente ...
```

**Fase 2 (2026-02-01):** Agregar warning en runtime:

```python
import warnings

def verificar_rol(usuario, roles_permitidos: list[str]):
    warnings.warn(
        "verificar_rol() está deprecado. Usar validar_scope(). "
        "Fecha de muerte: 2026-04-01",
        DeprecationWarning,
        stacklevel=2
    )
    # ... código existente ...
```

**Fase 3 (2026-04-01):** Convertir en excepción:

```python
def verificar_rol(usuario, roles_permitidos: list[str]):
    raise NotImplementedError(
        "verificar_rol() fue eliminado el 2026-04-01. "
        "Usar validar_scope() según FASE 1."
    )
```

### 1.4 Regla de CI/Linter

```yaml
# .github/workflows/aup-compliance.yml
- name: Check ROL-001 compliance
  run: |
    # Buscar usos prohibidos de rol
    if grep -rn "verificar_rol\|usuario\.rol ==" backend/routers/; then
      echo "❌ ROL-001: Uso de rol para autorización detectado"
      exit 1
    fi
```

---

## 2. MIDDLEWARE DE CONTEXTO OBLIGATORIO

### 2.1 Propósito

Ejecutar `SET app.tenant_id` ANTES de cualquier query que dependa de RLS.

### 2.2 Diseño

```
┌─────────────────────────────────────────────────────────────┐
│                        REQUEST                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  1. get_current_user()                                       │
│     → Extrae identity_id de JWT                              │
│     → Reconstruye Usuario desde DB                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. resolve_tenant_context()         [NUEVO]                │
│     → Obtiene tenant_id de: path param / query / body        │
│     → Valida que usuario tiene scope en ese tenant           │
│     → Ejecuta SET app.tenant_id = <tenant_id>                │
│     → FALLA si no puede resolver/validar tenant              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. ENDPOINT                                                 │
│     → Queries con RLS activo                                 │
│     → tenant_id ya está en contexto de sesión DB             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Especificación del Dependency

**Archivo:** `backend/core/tenant/context.py`

**Función:** `set_tenant_context()`

**Contrato:**

| Entrada | Salida | Falla |
|---------|--------|-------|
| `db: Session` | `tenant_id: str` | HTTPException 400 si no hay tenant |
| `current_user: Usuario` | (efecto: SET app.tenant_id) | HTTPException 403 si no hay scope |
| `tenant_id: str` (de path/query) | | HTTPException 500 si SET falla |

**Comportamiento:**

1. Si `tenant_id` no viene en request → 400 Bad Request
2. Si usuario no tiene scope activo en `tenant_id` → 403 Forbidden
3. Si `SET app.tenant_id` falla → 500 Internal Error
4. Si todo OK → retorna `tenant_id` y continúa

**Por qué ANTES de queries:**

RLS en PostgreSQL evalúa `current_setting('app.tenant_id')` al momento del query.
Si el SET no se ejecutó, `current_setting(..., true)` retorna NULL y:
- Políticas USING pueden fallar silenciosamente
- Datos pueden filtrarse incorrectamente

El SET debe ocurrir en la MISMA conexión que ejecutará queries.

### 2.4 Pseudocódigo

```python
async def set_tenant_context(
    tenant_id: str,  # De path/query param
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> str:
    """
    Dependency que configura contexto de tenant para RLS.
    
    DEBE usarse en todo endpoint que opere sobre datos de tenant.
    """
    # 1. Validar scope
    if not validar_scope(db, current_user, tenant_id, AccessLevel.LECTURA):
        raise HTTPException(403, "Sin scope en tenant")
    
    # 2. Ejecutar SET
    db.execute(text(f"SET app.tenant_id = :tid"), {"tid": tenant_id})
    
    # 3. Retornar tenant_id para uso en endpoint
    return tenant_id
```

### 2.5 Excepciones al Middleware

| Endpoint | Razón | Alternativa |
|----------|-------|-------------|
| `POST /auth/login` | No hay sesión aún | N/A |
| `GET /health` | Diagnóstico | N/A |
| Endpoints MSP globales | Operan sobre múltiples tenants | `SET app.tenant_id = 'msp_global'` |

---

## 3. PATRÓN CANÓNICO DE ENDPOINT

### 3.1 Flujo Estándar

```
┌─────────────────────────────────────────────────────────────┐
│ PASO 1: RESOLVER IDENTIDAD                    [OBLIGATORIO] │
│         current_user = Depends(get_current_user)            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 2: RESOLVER TENANT                       [OBLIGATORIO] │
│         tenant_id = path param / query param / body         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 3: SET app.tenant_id                     [OBLIGATORIO] │
│         Depends(set_tenant_context)                         │
│         → Valida scope implícitamente                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 4: VALIDAR NIVEL DE SCOPE                [CONDICIONAL] │
│         validar_scope(db, user, tenant, AccessLevel.X)      │
│         → Si operación requiere nivel > LECTURA             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 5: EVALUAR GOBIERNO                      [CONDICIONAL] │
│         puede_ejecutar_accion(db, user, token, accion, ...) │
│         → Si operación tiene límites de política            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 6: EJECUTAR ACCIÓN                       [OBLIGATORIO] │
│         service.operacion(db, ...)                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PASO 7: REGISTRAR EVENTO                      [CONDICIONAL] │
│         registrar_evento(db, identity, token, tenant, ...)  │
│         → Si operación es auditable                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Cuándo Aplica Cada Paso

| Paso | Lecturas | Mutaciones | Gobierno |
|------|----------|------------|----------|
| 1. Resolver identidad | ✅ | ✅ | ✅ |
| 2. Resolver tenant | ✅ | ✅ | ✅ |
| 3. SET app.tenant_id | ✅ | ✅ | ✅ |
| 4. Validar nivel scope | ⚠️ Si > LECTURA | ✅ | ✅ |
| 5. Evaluar gobierno | ❌ | ⚠️ Si tiene límites | ✅ |
| 6. Ejecutar acción | ✅ | ✅ | ✅ |
| 7. Registrar evento | ⚠️ Opcional | ✅ | ✅ |

### 3.3 Plantilla de Endpoint Alineado

```python
@router.post("/condominio/{condominio_id}/visitas")
def crear_visita(
    condominio_id: str,
    data: VisitaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),  # PASO 1
    _tenant: str = Depends(set_tenant_context),          # PASO 2+3
):
    """Endpoint alineado con arquitectura AUP."""
    
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # PASO 4: Validar nivel de scope (requiere ADMIN para crear)
    if not validar_scope(db, current_user, condominio_id, AccessLevel.ADMIN_CONDOMINIO):
        registrar_evento(db, current_user, token, condominio_id,
            entidad="visita", entidad_id="pending",
            accion="crear", resultado="denegado",
            motivo="Scope insuficiente")
        raise HTTPException(403, "Scope insuficiente")
    
    # PASO 5: Evaluar gobierno (si aplica límite de visitas)
    permitido, motivo = puede_ejecutar_accion(
        db, current_user, token,
        accion="crear_visita",
        tenant_id=condominio_id
    )
    if not permitido:
        raise HTTPException(403, f"Gobierno denegó: {motivo}")
    
    # PASO 6: Ejecutar
    visita = visita_service.crear_visita(db, data)
    
    # PASO 7: Registrar evento
    registrar_evento(db, current_user, token, condominio_id,
        entidad="visita", entidad_id=visita.visita_id,
        accion="crear", resultado="exito",
        metadata={"visitante": data.nombre_visitante})
    
    return visita
```

---

## 4. PLAN DE MIGRACIÓN POR PRIORIDAD

### 4.1 Clasificación de Endpoints

#### CRÍTICOS (Migrar primero)

Operaciones que modifican estado de gobierno o datos sensibles.

| Endpoint | Archivo | Línea | Problema Actual |
|----------|---------|-------|-----------------|
| `POST /condominios/` | condominios_router.py | 51 | `verificar_rol` + sin SET tenant |
| `POST /visitas/` | visitas_router.py | 28 | Parcialmente correcto, falta SET |

#### SENSIBLES (Migrar segundo)

Lecturas protegidas y operaciones sobre datos de tenant.

| Endpoint | Archivo | Línea | Problema Actual |
|----------|---------|-------|-----------------|
| `GET /visitas/condominio` | visitas_router.py | 140 | `verificar_rol` |
| `GET /visitas/mis-visitas` | visitas_router.py | 103 | `verificar_rol` + TODO comentado |
| `GET /condominios/` | condominios_router.py | 20 | `verificar_rol` |
| `POST /evidencias/` | evidencias_router.py | 26 | `verificar_rol` |
| `POST /qr/validar` | qr_router.py | 92 | `verificar_rol` |

#### SECUNDARIOS (Migrar tercero)

Operaciones de menor riesgo.

| Endpoint | Archivo | Línea | Problema Actual |
|----------|---------|-------|-----------------|
| `POST /preregistro/` | preregistro_router.py | 28 | `verificar_rol` |
| `GET /preregistro/mis-preregistros` | preregistro_router.py | 76 | `verificar_rol` |
| `POST /qr/generar` | qr_router.py | 27 | `verificar_rol` |

### 4.2 Orden de Migración

```
SEMANA 1: Infraestructura
├── Crear backend/core/tenant/context.py
├── Implementar set_tenant_context()
├── Agregar deprecation warning a verificar_rol()
└── Agregar regla CI ROL-001

SEMANA 2: Endpoints CRÍTICOS
├── POST /condominios/
└── POST /visitas/

SEMANA 3: Endpoints SENSIBLES
├── GET /visitas/condominio
├── GET /visitas/mis-visitas
├── GET /condominios/
├── POST /evidencias/
└── POST /qr/validar

SEMANA 4: Endpoints SECUNDARIOS + Limpieza
├── POST /preregistro/
├── GET /preregistro/mis-preregistros
├── POST /qr/generar
└── Verificar cobertura 100%
```

### 4.3 Validación por Migración

Para cada endpoint migrado, verificar:

| Check | Comando/Método |
|-------|----------------|
| No usa `verificar_rol` | `grep -n "verificar_rol" <archivo>` |
| Usa `set_tenant_context` | `grep -n "set_tenant_context" <archivo>` |
| Tiene evento de auditoría | `grep -n "registrar_evento" <archivo>` |
| Tests pasan | `pytest tests/routers/test_<router>.py` |
| RLS activo | Test con tenant incorrecto → 403 o vacío |

---

## 5. CRITERIOS DE ACEPTACIÓN

### 5.1 Endpoint Alineado

Un endpoint se considera "alineado con AUP" si cumple TODOS:

| Criterio | Verificación |
|----------|--------------|
| **AUP-A1** | No contiene `verificar_rol()` |
| **AUP-A2** | No contiene `usuario.rol ==` ni `usuario.rol in` |
| **AUP-A3** | Usa `Depends(get_current_user)` |
| **AUP-A4** | Usa `Depends(set_tenant_context)` si opera sobre tenant |
| **AUP-A5** | Usa `validar_scope()` si requiere nivel > LECTURA |
| **AUP-A6** | Usa `puede_ejecutar_accion()` si tiene límites de política |
| **AUP-A7** | Usa `registrar_evento()` si es mutación o acción sensible |

### 5.2 Cuándo Bloquear Merge

| Condición | Acción |
|-----------|--------|
| PR contiene `verificar_rol()` en código nuevo | ❌ Bloquear |
| PR modifica endpoint sin alinearlo | ❌ Bloquear |
| PR agrega endpoint sin patrón canónico | ❌ Bloquear |
| PR elimina `set_tenant_context` de endpoint existente | ❌ Bloquear |
| PR elimina `registrar_evento` de mutación | ❌ Bloquear |

### 5.3 Señales de Incumplimiento

| Señal | Significa |
|-------|-----------|
| `grep "verificar_rol" backend/routers/` retorna resultados | Código legacy no migrado |
| Test con tenant incorrecto retorna datos | RLS no activo |
| Operación crítica sin evento en `events_aup` | Auditoría incompleta |
| `usuario.rol` usado en condicional | Violación ROL-001 |

### 5.4 Checklist de PR

```markdown
## Checklist AUP Compliance

- [ ] No uso `verificar_rol()` 
- [ ] No uso `usuario.rol` para decisiones
- [ ] Uso `Depends(get_current_user)` para identidad
- [ ] Uso `Depends(set_tenant_context)` para tenant (si aplica)
- [ ] Uso `validar_scope()` para nivel de acceso (si aplica)
- [ ] Uso `puede_ejecutar_accion()` para gobierno (si aplica)
- [ ] Uso `registrar_evento()` para mutaciones
- [ ] Tests verifican aislamiento de tenant
```

---

## 6. RIESGOS DURANTE LA MIGRACIÓN

### 6.1 Qué Puede Romperse

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Endpoint retorna 403 donde antes funcionaba | ALTA | ALTO | Verificar que scopes existen en BD |
| Queries retornan vacío por RLS mal configurado | MEDIA | ALTO | Test de integración antes de merge |
| Performance degradada por SET adicional | BAJA | BAJO | SET es operación trivial |
| Eventos duplicados | MEDIA | BAJO | Verificar idempotencia |

### 6.2 Qué NO Debe Romperse

| Invariante | Verificación |
|------------|--------------|
| Login sigue funcionando | Test `POST /auth/login` |
| Usuarios con scope correcto pueden operar | Test de happy path |
| Usuarios sin scope reciben 403 | Test de autorización |
| Datos de un tenant no visibles desde otro | Test de aislamiento |
| Eventos se registran en `events_aup` | Query post-operación |

### 6.3 Qué NO Intentar Arreglar Ahora

| Tentación | Por qué NO |
|-----------|------------|
| Refactorizar services | Fuera de alcance; solo routers |
| Optimizar queries | No es objetivo de esta fase |
| Agregar features de seguridad (MFA, rate limit) | Requiere diseño separado |
| Migrar a OAuth2 externo | Cambio arquitectónico mayor |
| Renombrar `rol` a `identity_label` en BD | Migración separada (FASE 1) |
| Implementar FK entre dominios AUP | Decisión de diseño, no implementación |

### 6.4 Plan de Rollback

Si un endpoint migrado causa problemas en producción:

1. **Revertir commit específico** (no todo el branch)
2. **Agregar endpoint a lista de excepciones** temporales
3. **Documentar problema** en issue
4. **Corregir y re-migrar** en siguiente iteración

No revertir la infraestructura (`set_tenant_context`, reglas CI) por un endpoint problemático.

---

## 7. VERIFICACIÓN FINAL

### 7.1 Comando de Verificación Global

```bash
#!/bin/bash
# scripts/verify_aup_alignment.sh

echo "=== Verificación de Alineación AUP ==="

# ROL-001: No uso de verificar_rol en routers
echo -n "ROL-001 (verificar_rol): "
if grep -rn "verificar_rol" backend/routers/ > /dev/null 2>&1; then
    echo "❌ FALLA - Uso detectado"
    grep -rn "verificar_rol" backend/routers/
else
    echo "✅ OK"
fi

# ROL-002: No uso de usuario.rol para decisiones
echo -n "ROL-002 (usuario.rol): "
if grep -rn "usuario\.rol ==" backend/routers/ > /dev/null 2>&1; then
    echo "❌ FALLA - Uso detectado"
else
    echo "✅ OK"
fi

# TENANT-001: Uso de set_tenant_context
echo -n "TENANT-001 (set_tenant_context): "
count=$(grep -rn "set_tenant_context" backend/routers/ | wc -l)
echo "✅ $count usos encontrados"

# EVENT-001: Uso de registrar_evento en mutaciones
echo -n "EVENT-001 (registrar_evento): "
count=$(grep -rn "registrar_evento" backend/routers/ | wc -l)
echo "✅ $count usos encontrados"

echo "=== Fin de Verificación ==="
```

### 7.2 Definición de "Migración Completa"

La migración se considera COMPLETA cuando:

1. `grep "verificar_rol" backend/routers/` retorna 0 resultados
2. Todos los endpoints con tenant usan `set_tenant_context`
3. Todas las mutaciones tienen `registrar_evento`
4. CI bloquea PRs que violen criterios
5. `verificar_rol()` lanza `DeprecationWarning`

### 7.3 Fecha Objetivo

| Hito | Fecha |
|------|-------|
| Infraestructura lista | 2026-01-15 |
| Endpoints CRÍTICOS migrados | 2026-01-22 |
| Endpoints SENSIBLES migrados | 2026-01-29 |
| Endpoints SECUNDARIOS migrados | 2026-02-05 |
| `verificar_rol()` emite warning | 2026-02-01 |
| `verificar_rol()` lanza excepción | 2026-04-01 |
| Migración COMPLETA | 2026-02-05 |

---

## 8. RESUMEN EJECUTIVO

| Componente | Estado Actual | Estado Objetivo | Acción |
|------------|---------------|-----------------|--------|
| `verificar_rol()` | Usado en 9 endpoints | Eliminado | Deprecar → Warning → Excepción |
| `set_tenant_context` | No existe | Obligatorio | Crear dependency |
| `validar_scope()` | Existe, subutilizado | Usado en todos los endpoints | Reemplazar verificar_rol |
| `registrar_evento()` | Existe, parcial | Usado en todas las mutaciones | Agregar donde falta |
| RLS activo | Especificado, no activo | Activo vía SET | Middleware de contexto |

**Meta final:** Cada endpoint debe poder afirmar:

> "Soy AUP-compliant: no dependo de rol, respeto tenant isolation, dejo rastro forense."

---

**FIN DEL PLAN DE ALINEACIÓN — FASE 6**
