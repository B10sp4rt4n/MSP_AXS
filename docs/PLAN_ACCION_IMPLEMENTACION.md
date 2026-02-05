# PLAN DE ACCIÓN: PILOTO AUP EN 2 SEMANAS

**Versión:** 2.0.0-piloto  
**Fecha:** 2026-01-06  
**Tipo:** Plan de Ejecución Pragmático  
**Estado:** Activo

---

## 🎯 OBJETIVO PRINCIPAL

**Construir en 2 semanas un PILOTO FUNCIONAL con 1 tenant real.**

NO es un plan de migración completa.  
NO es una limpieza arquitectónica.  
**ES** una preparación para validar AUP con usuarios reales.

### Criterios de éxito del piloto

✅ Aislamiento multi-tenant verificable  
✅ Autorización por scope + contexto (NO rol)  
✅ RLS activo en queries críticos  
✅ Trazabilidad mínima funcionando  
✅ **0 fugas de datos entre tenants**  

**Duración estimada:** 10 días hábiles (1 desarrollador)

---

## ⚠️ PRINCIPIOS DE DECISIÓN (NO ROMPER)

| Principio | Acción |
|-----------|--------|
| **Si no afecta el piloto** | No se hace aún |
| **Si no reduce riesgo** | Se pospone |
| **Estabilidad > Features** | Siempre |
| **20/80** | 20% del código que cubre 80% del riesgo |
| **Deuda técnica** | Aceptable si está documentada |

---

## ❌ LO QUE NO VAMOS A HACER (TODAVÍA)

| ❌ NO Hacer | ✅ Hacer después del piloto |
|------------|----------------------------|
| Migrar todos los routers legacy | Solo endpoints críticos del piloto |
| Exigir 80% coverage global | Solo tests de aislamiento multi-tenant |
| Integrar AUP_GOV completo | Solo validación de scope básica |
| Rehacer UI | Usar UI existente |
| Optimizaciones prematuras | Observar primero en piloto |
| CI/CD complejo | Linter básico ROL-001 |

---

## 📋 FASES DEL PLAN

### **FASE 0: LÍMITES CLAROS** (30 minutos - HOY)

**Objetivo:** Entender qué endpoints SÍ necesita el piloto.

#### Tarea 0.1: Definir alcance del piloto

**Preguntas a responder:**
1. ¿Qué tenant real usaremos? (nombre/ID)
2. ¿Cuántos usuarios? (5-10 recomendado)
3. ¿Qué flujos van a probar?
   - [ ] Login
   - [ ] Registrar visita
   - [ ] Ver residentes
   - [ ] Ver eventos
   - [ ] Otro: ___________

**Documentar en:** `docs/PILOTO_ALCANCE.md`

```markdown
# ALCANCE PILOTO

**Tenant:** Condominio Las Flores (ID: condo-123)
**Usuarios:** 8 (1 admin + 6 residentes + 1 caseta)
**Duración:** 72 horas
**Fecha inicio:** 2026-01-13

## Endpoints críticos (SOLO estos migrar)
- POST /auth/login
- POST /visitas/registrar
- GET /condominios/{id}/residentes
- GET /eventos/auditoria

## Endpoints secundarios (NO tocar)
- Todo lo demás
```

**Criterio de aceptación:**
- [ ] Documento creado
- [ ] Lista de endpoints <= 5
- [ ] Equipo alineado

**Tiempo:** 30 minutos

---

### **FASE 1: FUNDACIÓN CRÍTICA** (Día 1-2)

**Objetivo:** Que el sistema NO PUEDA violar multi-tenancy, aunque el dev se equivoque.

#### ✅ Tarea 1.1: Implementar `set_tenant_context()` (PRIORIDAD MÁXIMA)

**Este es el archivo más importante del proyecto.**

**Archivo nuevo:** `backend/core/tenant/context.py`

**Por qué primero:**
- Sin esto, RLS no funciona
- Sin RLS, hay fuga de datos entre tenants
- Es bloqueante para todo lo demás

**Código completo:**
```python
# backend/core/tenant/context.py
```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.db.core.connection import get_db
from backend.core.auth.dependencies import get_current_user
from backend.db.core.models import Usuario
from backend.core.scope.validator import validar_scope
from backend.schemas.scope import AccessLevel

async def set_tenant_context(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> str:
    """
    Dependency que configura contexto de tenant para RLS.
    
    DEBE usarse en todo endpoint que opere sobre datos de tenant.
    
    Flujo:
    1. Valida que usuario tiene scope en tenant_id
    2. Ejecuta SET app.tenant_id para activar RLS
    3. Retorna tenant_id para uso en endpoint
    
    Excepciones:
    - 403: Usuario sin scope en tenant
    - 500: Fallo al ejecutar SET
    """
    # 1. Validar scope
    if not validar_scope(db, current_user, tenant_id, AccessLevel.LECTURA):
        raise HTTPException(
            status_code=403,
            detail=f"Usuario no tiene scope en tenant {tenant_id}"
        )
    
    # 2. Ejecutar SET para RLS
    try:
        db.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_id})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error configurando tenant context: {str(e)}"
        )
"""
Contexto de tenant para RLS multi-tenant.

ESTE ES EL ARCHIVO MÁS CRÍTICO DEL SISTEMA.
Sin esto, hay fuga de datos entre tenants.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from backend.db.core.connection import get_db
from backend.core.auth.dependencies import get_current_user
from backend.db.core.models import Usuario
from backend.core.scope.validator import validar_scope
from backend.sc2: Deprecar `verificar_rol()` (SIN romper legacy)

**Archivo:** Buscar dónde está definido `verificar_rol()`

**Acción simple:**
```python
import warnings

def verificar_rol(usuario, roles_permitidos: list[str]):
    """
    ⛔ DEPRECADO - Usar validar_scope()
    Fecha de muerte: Post-piloto
    """
    warnings.warn(
        "verificar_rol() deprecado. Ver docs/ESPECIFICACION_CAMPO_ROL.md",
        DeprecationWarning,
        stacklevel=2
    )
    # ... código existente SIN CAMBIOS ...
```

**NO hacer:**
- ❌ Eliminar la función
- ❌ Convertir en excepción
- ❌ Migrar todos los usos

**SÍ hacer:**
- ✅ Warning discreto
- ✅ Docstring claro
- ✅ Todo sigue funcionando

**Tiempo:** 15 minutos

---

#### ✅ Tarea 1.3: Migrar UN endpoint crítico

**Cuál:** El endpoint que SÍ va a usar el piloto (según Fase 0)

**Ejemplo:** `POST /visitas/registrar`

**ANTES (legacy) Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> str:
    """
    Configura contexto de tenant para RLS.
    
    FLUJO:
    1. Valida scope del usuario
    2. Ejecuta SET app.tenant_id
    3. Retorna tenant_id
    
    CRÍTICO: Este dependency DEBE estar en todo endpoint multi-tenant.
    """
    # 1. Validar scope
    logger.info(f"Validando scope: user={current_user.id} tenant={tenant_id}")
    
    if not validar_scope(db, current_user, tenant_id, AccessLevel.LECTURA):
        logger.warning(f"ACCESO DENEGADO: user={current_user.id} tenant={tenant_id}")
        raise HTTPException(
            status_code=403,
            detail=f"Sin acceso a tenant {tenant_id}"
        )
    
    # 2. SET app.tenant_id (RLS)
    try:
        db.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_id})
        logger.info(f"✅ RLS activado: tenant={tenant_id}")
    except Exception as e:
        logger.error(f"❌ ERROR SET app.tenant_id: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno de aislamiento multi-tenant"
        )
    
    return tenant_id
```

**Probar manualmente:**
```python
# tests/manual_test_context.py
from backend.core.tenant.context import set_tenant_context

# Debe fallar con 403
set_tenant_context(tenant_id="otro-tenant", current_user=usuario_sin_scope)

# Debe pasar y loguear "✅ RLS activado"
set_tenant_context(tenant_id="mi-tenant", current_user=usuario_con_scope)
```

**Criterio de aceptación:**
- [ ] Archivo creado
- [ ] Logs claros (grep-eables)
- [ ] 403 si no hay scope
- [ ] SET se ejecuta si hay scope

**Tiempo:** 2 horas (incluye pruebas manuales)

**Criterio de aceptación:**
- [ ] Usa `Depends(set_tenant_context)`
- [ ] NO usa `verificar_rol()`
- [ ] RLS filtra correctamente
- [ ] Tests pasan

**Tiempo estimado:** 60 minutos

**Objetivo:** Ver el sistema vivir en producción temprana.

#### ✅ Tarea 2.1: Migrar SOLO endpoints del piloto

**Lista del alcance (Fase 0):**
```bash
# Ejemplo - ajustar según tu Fase 0
- POST /auth/login
- POST /visitas/registrar  # Ya está ✅
- GET /condominios/{id}/residentes
- GET /eventos/auditoria
```

**Proceso por endpoint:**
1. Agregar `Depends(set_tenant_context)`
2. Quitar `verificar_rol()`
3. Probar manualmente
4. Next

**❌ NO migrar:**
- Endpoints no usados en piloto
- Endpoints de admin MSP (por ahora)
- Features secundarias

**Tiempo:** 2-3 días (3-4 endpoints)

---

#### ✅ Tarea 2.2: Deploy a staging/production

**Según:** [DEPLOYMENT.md](../DEPLOYMENT.md)

**Pasos mínimos:**
1. Crear bases en Neon (aup_core, aup_event, aup_gov)
2. Ejecutar migraciones bootstrap
3. Deploy a Railway
4. Health check pasa

**Validar:**
```bash
curl https://tu-api.railway.app/health
# Esperado: {"status": "healthy"}
```

**Tiempo:** 3-4 horas

---

#### ✅ Tarea 2.3: Arrancar piloto real (72 horas)

**Configuración:**
- 1 tenant real
- 5-10 usuarios
- Monitoreo manual intensivo

**Métricas a observar:**

1. **Aislamiento multi-tenant**
   ```bash
   # Buscar en logs
   grep "ACCESO DENEGADO" logs.txt
   grep "RLS activado" logs.txt
   
   # Debe ser:
   # - 0 fugas entre tenants
   # - N activaciones RLS (1 por request)
   ```

2. **Errores**
   ```bash
   grep "ERROR\|500\|403" logs.txt | wc -l
   # Target: < 5 en 72h
   ```

3. **Latencia**
   ```bash
   # Si tienes APM, mirar p95
   # Si no, revisar logs de tiempo de respuesta
   # Target: < 500ms p95
   ```

**Monitoreo simple:**
```bash
# Cada 2 horas durante piloto
tail -f logs.txt | grep -E "ERROR|RLS|403|500"
```

**Tiempo:** 3 días (monitoreo + ajustes reactivos)

---

**🎯 CHECKPOINT DÍA 7:**
- [ ] Piloto corrió 72h
- [ ] 0 fugas multi-tenant detectadas
- [ ] < 5 errores críticos
- [ ] Usuarios pudieron usar el sistema

**Decisión GO/NO-GO:**
- ✅ GO: Continuar a consolidación
- ❌ NO-GO: Volver a Fase 1, corregir problemas

---

### **FASE 3: CONSOLIDACIÓN** (Día 8-10)

**Objetivo:** Cerrar huecos detectados en el piloto.

#### ✅ Tarea 3.1: Corregir issues del piloto

**Basado en observaciones reales:**
- ¿RLS falló en algún endpoint? → Corregir
- ¿Mensajes de error confusos? → Mejorar
- ¿Scope mal configurado? → Ajustar

**NO hacer:**
- ❌ Agregar features nuevas
- ❌ Optimizar sin evidencia
- ❌ "Limpiar código" por estética

**Tiempo:** 1-2 días

---

#### ✅ Tarea 3.2: CI básico (linter ROL-001)

**Solo si el piloto fue estable.**

**Archivo:** `.github/workflows/aup-lint.yml`
```yaml
name: AUP Lint - ROL-001

on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Detectar uso de verificar_rol()
        run: |
          if grep -rn "verificar_rol" backend/routers/ --include="*.py"; then
            echo "❌ verificar_rol() detectado"
            exit 1
          fi
          echo "✅ No violations"
```

**Tiempo:** 30 minutos

---

#### ✅ Tarea 3.3: Documentar decisiones técnicas

**Archivo:** `docs/DECISIONES_PILOTO.md`

**Contenido:**
```markdown
# Decisiones Técnicas del Piloto

## Qué se migró
- Endpoint X: Porque era crítico
- Endpoint Y: Porque lo usaba el piloto

## Qué NO se migró (y por qué)
- Admin MSP: No se usa en piloto
- Features Z: Legacy estable, sin riesgo

## Problemas encontrados en piloto
1. RLS falló en endpoint X → Solucionado con...
2. Scope mal configurado → Documentado en...

## Deuda técnica aceptada
- [ ] Migrar resto de endpoints (post-piloto)
- [ ] Integrar AUP_GOV completo (post-piloto)
- [ ] Eliminar verificar_rol() (fecha: TBD)
```

**Tiempo:** 1 hora

---

**🎯 CHECKPOINT DÍA 10:**
- [ ] Issues del piloto corregidos
- [ ] CI básico funcionando
- [ ] Decisiones documentadas
- [ ] Sistema estable para producción

---

## 🚦 DESPUÉS DEL PILOTO (Post Día 10)

**Solo si el piloto fue exitoso:**

### Siguiente fase (Semana 3-4)
- Migrar endpoints restantes
- Integrar AUP_GOV completo
- Aumentar coverage a 80%
- Convertir verificar_rol() en excepción

### Features comerciales (Mes 2)
- Planes Free/Pro/Enterprise
- Delegaciones temporales
- Dashboard de métricas
- UI mejoradas

---

## 🎯 HOJA DE RUTA VISUAL

```
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1: INMEDIATA (1-2 días)                                   │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Deprecar verificar_rol()                        [30 min]    │
│  ✅ Crear set_tenant_context()                      [90 min]    │
│  ✅ Migrar 1 endpoint crítico                       [60 min]    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2: CORTO PLAZO (1 semana)                                 │
├─────────────────────────────────────────────────────────────────┤
│  ✅ CI/Linter ROL-001                               [45 min]    │
│  ✅ Migrar 18 endpoints principales                 [3-4 días]  │
│  ✅ Tests de integración                            [2 horas]   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FASE 3: MEDIO PLAZO (2-3 semanas)                              │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Integrar AUP_GOV                                [1 semana]  │
│  ✅ Migración completa legacy                       [1 semana]  │
│  ✅ Smoke test pre-piloto                           [2 días]    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  FASE 4: PREPARACIÓN PILOTO (1 mes)                             │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Deployment Railway/Neon                         [4 horas]   │
│  ✅ Documentación operativa                         [2 días]    │
│  ✅ Micro-piloto controlado                         [3 días]    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    🚀 PILOTO COMPLETO
```

---

## 🔥 PRIORIDAD ABSOLUTA (4 horas hoy)

Si solo tienes **4 horas disponibles hoy**, ejecutar en este orden:

### 1. **Implementar `set_tenant_context()`** (90 min)
```bash
# Crear archivo
touch backend/core/tenant/context.py
# Implementar según Tarea 1.2
# Probar manualmente
```

### 2. **Migrar endpoint `POST /visitas/registrar`** (60 min)
```bash
# Editar backend/routers/visitas.py
# Agregar Depends(set_tenant_context)
# Eliminar verificar_rol()
# Probar con Postman/curl
```

### 3. **Test de integración básico** (60 min)
```bash
# Crear tests/integration/test_tenant_context.py
# Implementar test_set_tenant_context_ejecuta_correctamente()
pytest tests/integration/test_tenant_context.py -v
```

### 4. **Deprecar `verificar_rol()`** (30 min)
```bash
# Agregar docstring de deprecación
# Commit y push
git add .
git commit -m "feat: deprecar verificar_rol() + crear set_tenant_context()"
```

---

## 🎯 CRITERIOS DE ÉXITO DEL PILOTO

**Mínimos absolutos:**

| Criterio | Target | Cómo verificar |
|----------|--------|----------------|
| **Fuga multi-tenant** | 0 | `grep "ACCESO DENEGADO" logs.txt` |
| **RLS activo** | 100% requests | `grep "RLS activado" logs.txt` |
| **Errores críticos** | < 5 en 72h | `grep "ERROR\|500" logs.txt \| wc -l` |
| **Latencia p95** | < 500ms | Logs o APM simple |
| **Piloto completo** | 72h corriendo | Reloj |

**NO medir (aún):**
- ❌ Coverage global
- ❌ Performance micro-optimizada
- ❌ Endpoints no usados

---

## 🚨 SEÑALES DE ALERTA (STOPPER)

**Detener TODO si aparece:**

1. **Usuario ve datos de otro tenant**
   → Problema crítico de aislamiento
   → Rollback inmediato

2. **> 10 errores 500 en 1 hora**
   → Sistema inestable
   → Revisar Fase 1

3. **RLS no se activa**
   → `grep "RLS activado" logs.txt` retorna 0
   → Problema en set_tenant_context()

4. **Latencia > 2 segundos**
   → Problema de performance crítico
**Documentos técnicos:**
- [FASE6_PLAN_ALINEACION.md](FASE6_PLAN_ALINEACION.md) - Especificación completa
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment a Neon/Railway
- [ESPECIFICACION_CAMPO_ROL.md](ESPECIFICACION_CAMPO_ROL.md) - Por qué NO usar rol

**Post-piloto:**
- [AUP_GOV_INTEGRACION_SUMMARY.md](AUP_GOV_INTEGRACION_SUMMARY.md) - Gobierno
- [SMOKE_TEST_PREPILOTO.md](SMOKE_TEST_PREPILOTO.md) - Tests exhaustivos

---

## 📞 SOPORTE

| Situación | Acción |
|-----------|--------|
| Duda técnica | Revisar [FASE6_PLAN_ALINEACION.md](FASE6_PLAN_ALINEACION.md) |
| Fuga multi-tenant | ROLLBACK inmediato, revisar Fase 1 |
| Piloto inestable | NO avanzar, corregir fundación |
| ¿Migrar endpoint X? | Si NO está en piloto → NO migrar |

---

**Última actualización:** 2026-01-06  
**Próxima revisión:** 2026-01-16 (post-piloto)  
**Autor:** @B10sp4rt4n  
**Versión:** 2.0.0-piloto (enfoque pragmático)
- Estabilidad > Completitud
- Evidencia > Suposiciones
- Iteración > Big Bang
- Piloto real > Tests sintéticos
- Deuda técnica documentada > Perfección prematura

---

## 🔗 REFERENCIAS

- [FASE6_PLAN_ALINEACION.md](FASE6_PLAN_ALINEACION.md) - Especificación técnica completa
- [AUP_GOV_INTEGRACION_SUMMARY.md](AUP_GOV_INTEGRACION_SUMMARY.md) - Integración de gobierno
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Guía de deployment
- [SMOKE_TEST_PREPILOTO.md](SMOKE_TEST_PREPILOTO.md) - Tests pre-piloto
- [ESPECIFICACION_CAMPO_ROL.md](ESPECIFICACION_CAMPO_ROL.md) - Por qué rol es metadata

---

**Última actualización:** 2026-01-06  
**Próxima revisión:** 2026-01-13
🗓️ CALENDARIO PRAGMÁTICO (2 SEMANAS)

```
DÍA 1-2: FUNDACIÓN
├─ set_tenant_context() [2h]
├─ Deprecar verificar_rol() [15min]
├─ Migrar 1 endpoint [45min]
└─ 3 smoke tests [1h]
   ⚠️ CHECKPOINT: Si falla, NO seguir

DÍA 3-5: MIGRACIÓN MÍNIMA
├─ Migrar 3-4 endpoints del piloto [2-3 días]
├─ Deploy a staging [4h]
└─ Validación manual

DÍA 6-8: PILOTO REAL (72h)
├─ Activar 1 tenant real
├─ 5-10 usuarios
├─ Monitoreo manual intensivo
└─ Registro de incidencias
   ⚠️ GO/NO-GO: Decidir si continuar

DÍA 9-10: CONSOLIDACIÓN
├─ Corregir issues del piloto
├─ CI básico
└─ Documentar decisiones

POST-PILOTO: EXPANSIÓN
├─ Migrar resto de endpoints
├─ AUP_GOV completo
└─ Features comerciales⚡ ACCIÓN INMEDIATA (PRÓXIMAS 4 HORAS)

**Orden de ejecución:**

### Hora 1-2: `set_tenant_context()`
```bash
mkdir -p backend/core/tenant
touch backend/core/tenant/__init__.py
touch backend/core/tenant/context.py

# Copiar código de Tarea 1.1
# Probar manualmente con Python REPL
```

### Hora 2.5-3: Migrar 1 endpoint
```bash
# Editar el endpoint del piloto
# Agregar Depends(set_tenant_context)
# Probar con curl
curl -X POST http://localhost:8000/visitas/registrar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'

# Ver logs - debe aparecer "✅ RLS activado"
```

### Hora 3-3.5: Smoke test
```bash
mkdir -p tests/smoke
touch tests/smoke/test_tenant_isolation.py

# Copiar 3 tests de Tarea 1.4
pytest tests/smoke/test_tenant_isolation.py -v
```

### Hora 3.5-4: Deprecar verificar_rol()
```bash
# Buscar donde está definido
grep -rn "def verificar_rol" backend/

# Agregar warning
# Commit
git add .
git commit -m "feat(aup): fundación multi-tenant - set_tenant_context()"
```

**Meta:** Al final de 4 horas, tener el sistema funcionando con RLS en 1 endpoint