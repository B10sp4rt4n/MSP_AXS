# EVALUACIÓN DE CÓDIGO — MSP_AXS

**Fecha:** 2026-01-01  
**Tipo:** Auditoría de Cumplimiento AUP  
**Alcance:** Backend Python (FastAPI)

---

## RESUMEN EJECUTIVO

| Categoría | Hallazgos | CRÍTICO | ALTO | MEDIO | BAJO |
|-----------|-----------|---------|------|-------|------|
| Uso de `rol` para autorización | 11 | 1 | 3 | 5 | 2 |
| Contexto de tenant (`app.tenant_id`) | 1 | 1 | 0 | 0 | 0 |
| Validación de scope | 3 | 0 | 1 | 2 | 0 |
| Emisión de eventos | 2 | 0 | 0 | 2 | 0 |
| **TOTAL** | **17** | **2** | **4** | **9** | **2** |

---

## 1. VIOLACIÓN CRÍTICA: USO DE `verificar_rol()` PARA AUTORIZACIÓN

### 1.1 Descripción

La función `verificar_rol()` en [backend/core/security.py](backend/core/security.py#L15-L17) usa `usuario.rol` para decidir autorización:

```python
def verificar_rol(usuario, roles_permitidos: list[str]):
    if usuario.rol not in roles_permitidos:
        raise HTTPException(status_code=403, detail="Acceso denegado")
```

**Esto viola directamente FASE 1 (ESPECIFICACION_CAMPO_ROL.md):**
- El campo `rol` (futuro `identity_label`) es **metadata descriptiva**
- NO debe usarse para decisiones de autorización
- La autorización debe basarse en `authorities_gov` y `user_tenant_scope`

### 1.2 Endpoints Afectados

| Archivo | Línea | Uso | Severidad |
|---------|-------|-----|-----------|
| [visitas_router.py](backend/routers/visitas_router.py#L129) | 129 | `verificar_rol(usuario, ["RESIDENTE"])` | ALTO |
| [visitas_router.py](backend/routers/visitas_router.py#L146) | 146 | `verificar_rol(usuario, ["ADMIN_CONDOMINIO", "GUARDIA"])` | ALTO |
| [condominios_router.py](backend/routers/condominios_router.py#L26) | 26 | `verificar_rol(usuario, ["MSP_ADMIN", "ADMIN_CONDOMINIO"])` | ALTO |
| [condominios_router.py](backend/routers/condominios_router.py#L64) | 64 | `verificar_rol(usuario, ["MSP_ADMIN"])` | MEDIO |
| [preregistro_router.py](backend/routers/preregistro_router.py#L28) | 28 | `verificar_rol(usuario, ["RESIDENTE"])` | MEDIO |
| [preregistro_router.py](backend/routers/preregistro_router.py#L76) | 76 | `verificar_rol(usuario, ["RESIDENTE"])` | MEDIO |
| [evidencias_router.py](backend/routers/evidencias_router.py#L26) | 26 | `verificar_rol(usuario, ["GUARDIA"])` | MEDIO |
| [qr_router.py](backend/routers/qr_router.py#L27) | 27 | `verificar_rol(usuario, ["ADMIN_CONDOMINIO", "RESIDENTE"])` | MEDIO |
| [qr_router.py](backend/routers/qr_router.py#L92) | 92 | `verificar_rol(usuario, ["GUARDIA"])` | MEDIO |

### 1.3 Violación Específica

**Documento violado:** ESPECIFICACION_CAMPO_ROL.md, Sección 4.2 (Antipatrones Prohibidos)

```python
# PROHIBIDO (actual):
if usuario.rol in ['GUARDIA', 'ADMIN_CONDOMINIO']:
    return True

# CORRECTO (AUP):
return validar_scope(db, usuario, tenant_id, AccessLevel.GUARDIA)
```

### 1.4 Riesgo

- **Amenaza ID-05 (Threat Model):** Uso de `identity_label` para autorización
- **Nivel:** ALTO
- **Responsable:** Aplicación

---

## 2. VIOLACIÓN CRÍTICA: `app.tenant_id` NO SE CONFIGURA

### 2.1 Descripción

El código **no ejecuta** `SET app.tenant_id` antes de queries SQL.

Busqué en todo el codebase y no encontré implementación de configuración de contexto RLS:

```
grep "app.tenant_id" backend/ → 0 resultados en código Python
```

### 2.2 Implicación

Según FASE 2 (SEGURIDAD_TRAZABILIDAD_DB.md):

> RLS depende de `SET app.tenant_id` correcto antes de cada operación.
> Si la aplicación no lo configura, las políticas RLS no filtran correctamente.

**El RLS especificado en FASE 2 NO está activo en la aplicación.**

### 2.3 Riesgo

- **Amenazas BD-01 y BD-02 (Threat Model):** `app.tenant_id` no seteado/manipulado
- **Nivel:** CRÍTICO
- **Responsable:** Aplicación

### 2.4 Corrección Requerida

```python
# En middleware o dependency antes de cada request:
async def set_tenant_context(
    db: Session,
    current_user: Usuario
):
    # Obtener tenant del scope activo del usuario
    scope = obtener_scope_usuario_en_tenant(db, current_user.usuario_id, tenant_id)
    if scope:
        db.execute(text(f"SET app.tenant_id = '{scope.tenant_id}'"))
```

---

## 3. INCONSISTENCIA: VALIDACIÓN DE SCOPE PARCIAL

### 3.1 Descripción

Algunos endpoints usan `validate_user_owns_resource_in_tenant()` correctamente,
pero otros usan `verificar_rol()` o ninguna validación.

### 3.2 Endpoints con Validación Correcta (AUP)

| Archivo | Endpoint | Validación |
|---------|----------|------------|
| [visitas_router.py](backend/routers/visitas_router.py#L28) | `POST /visitas/` | ✅ `validate_user_owns_resource_in_tenant()` |

### 3.3 Endpoints con Validación Incorrecta

| Archivo | Endpoint | Problema |
|---------|----------|----------|
| [visitas_router.py](backend/routers/visitas_router.py#L103) | `GET /visitas/mis-visitas` | Usa `verificar_rol` + comentario "TODO: hacer estrictamente AUP" |
| [visitas_router.py](backend/routers/visitas_router.py#L140) | `GET /visitas/condominio` | Usa solo `verificar_rol` |
| [condominios_router.py](backend/routers/condominios_router.py#L20) | `GET /condominios/` | Usa solo `verificar_rol` |

### 3.4 Código con TODO Explícito

[visitas_router.py](backend/routers/visitas_router.py#L120-L127):

```python
    # TODO: Hacer estrictamente AUP validando scope
    # validate_user_owns_resource_in_tenant(
    #     usuario=usuario,
    #     resource_tenant_id=usuario.condominio_id,
    #     db=db,
    #     required_level=AccessLevel.RESIDENTE
    # )
```

**El código reconoce que NO es AUP-compliant y tiene la corrección comentada.**

---

## 4. OBSERVACIÓN: EMISIÓN DE EVENTOS PARCIAL

### 4.1 Descripción

La emisión de eventos (`registrar_evento()`) está implementada en algunos endpoints pero no en todos.

### 4.2 Endpoints con Eventos Correctos

| Archivo | Endpoint | Eventos |
|---------|----------|---------|
| [auth_router.py](backend/routers/auth_router.py) | `POST /auth/login` | ✅ Login fallido, login exitoso |
| [visitas_router.py](backend/routers/visitas_router.py#L28) | `POST /visitas/` | ✅ Crear visita, denegado por scope |

### 4.3 Endpoints Sin Emisión de Eventos

| Archivo | Endpoint | Problema |
|---------|----------|----------|
| [visitas_router.py](backend/routers/visitas_router.py#L103) | `GET /visitas/mis-visitas` | Sin evento de lectura |
| [condominios_router.py](backend/routers/condominios_router.py#L20) | `GET /condominios/` | Sin evento de lectura |
| [condominios_router.py](backend/routers/condominios_router.py#L51) | `POST /condominios/` | Parcial (usa GOV pero no evento explícito) |

### 4.4 Riesgo

- **Amenaza EV-01 (Threat Model):** Omisión de evento crítico
- **Nivel:** MEDIO
- **Responsable:** Aplicación

---

## 5. POSITIVO: IMPLEMENTACIÓN CORRECTA

### 5.1 Estructura AUP Implementada

| Componente | Estado | Archivo |
|------------|--------|---------|
| `UserTenantScope` (modelo) | ✅ Correcto | [backend/db/models.py](backend/db/models.py#L117) |
| `validar_scope()` | ✅ Correcto | [backend/core/scope/validator.py](backend/core/scope/validator.py) |
| `registrar_evento()` | ✅ Correcto | [backend/core/event/registry.py](backend/core/event/registry.py) |
| `puede_ejecutar_accion()` (GOV) | ✅ Correcto | [backend/core/gov/facade.py](backend/core/gov/facade.py) |
| `get_current_user()` (SESSION) | ✅ Correcto | [backend/core/auth/dependencies.py](backend/core/auth/dependencies.py) |
| `AUPSessionGuard` (middleware) | ✅ Correcto | [backend/core/aup_runtime_blocks.py](backend/core/aup_runtime_blocks.py) |

### 5.2 Funciones Correctamente Diseñadas

- `calcular_hash_evento()` incluye `event_id` (cumple Enmienda v3.0.1)
- `hash_session_token()` para trazabilidad
- Jerarquía de `AccessLevel` correctamente definida
- `nivel_suficiente()` para comparación de niveles

---

## 6. MATRIZ DE CUMPLIMIENTO

### 6.1 Cumplimiento por Documento

| Documento | Cumplimiento | Notas |
|-----------|--------------|-------|
| FASE 1 (identity_label) | ❌ 30% | `verificar_rol()` viola especificación |
| FASE 2 (RLS/triggers) | ❌ 10% | `app.tenant_id` no se configura |
| FASE 3 (event sourcing) | ⚠️ 60% | Modelo correcto, emisión parcial |
| FASE 4 (threat model) | N/A | Documento de análisis, no código |
| FASE 5 (security posture) | N/A | Documento de análisis, no código |
| Acta de Límites | N/A | Documento de referencia |

### 6.2 Checklist de Pre-Producción (del Acta)

| # | Verificación | Estado |
|---|--------------|--------|
| 1 | La aplicación configura `app.tenant_id` en cada request | ❌ NO |
| 2 | La aplicación valida `tenant_id` contra JWT/sesión | ⚠️ Parcial |
| 3 | La aplicación consulta `authorities_gov` antes de operar | ⚠️ Solo en `crear_condominio` |
| 4 | La aplicación NO cachea permisos sin invalidación | ✅ No cachea |
| 5 | La aplicación NO usa `identity_label` para autorizar | ❌ Usa `verificar_rol()` |

---

## 7. RECOMENDACIONES DE REMEDIACIÓN

### 7.1 Prioridad CRÍTICA

1. **Eliminar `verificar_rol()`**
   - Reemplazar TODAS las llamadas por `validate_user_owns_resource_in_tenant()`
   - Marcar función como `@deprecated`

2. **Implementar middleware de contexto RLS**
   - Crear dependency que ejecute `SET app.tenant_id`
   - Aplicar a todos los endpoints que operan sobre datos de tenant

### 7.2 Prioridad ALTA

3. **Completar validación de scope**
   - Descomentar TODOs en `visitas_router.py`
   - Agregar validación a `condominios_router.py`

4. **Agregar emisión de eventos faltantes**
   - Operaciones de lectura sensibles
   - Operaciones de modificación sin evento

### 7.3 Prioridad MEDIA

5. **Agregar linter CI**
   - Regla: prohibir `usuario.rol` excepto en migración
   - Regla: prohibir `verificar_rol()`

6. **Renombrar columna `rol` → `identity_label`**
   - Ejecutar migración documentada en FASE 1
   - Crear vista de compatibilidad con fecha de muerte

---

## 8. CONCLUSIÓN

El código tiene la **arquitectura correcta** (modelos, validadores, registradores),
pero la **implementación en routers NO la usa consistentemente**.

| Aspecto | Arquitectura | Uso en Routers |
|---------|--------------|----------------|
| AUP_SESSION | ✅ Correcto | ✅ Usado |
| AUP_SCOPE | ✅ Correcto | ⚠️ Parcial |
| AUP_GOV | ✅ Correcto | ⚠️ Parcial |
| AUP_EVENT | ✅ Correcto | ⚠️ Parcial |
| RLS tenant | ✅ Especificado | ❌ No implementado |
| `identity_label` | ✅ Especificado | ❌ Aún usa `verificar_rol()` |

**Veredicto:** El sistema NO cumple con las especificaciones FASE 1-3 en su estado actual.
Las herramientas existen; los routers no las usan.

---

**FIN DE EVALUACIÓN DE CÓDIGO**
