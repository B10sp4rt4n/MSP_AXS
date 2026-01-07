# ALCANCE PILOTO AUP - 2 SEMANAS

**Versión:** 1.0.0  
**Fecha inicio:** 2026-01-13  
**Duración:** 72 horas (3 días)  
**Estado:** Planificación

---

## 🎯 OBJETIVO

Validar arquitectura AUP con **1 tenant real** en producción temprana.

**Criterio de éxito:** 0 fugas multi-tenant + sistema estable 72h

---

## 🏢 CONFIGURACIÓN DEL PILOTO

### Tenant seleccionado
**Nombre:** Condominio Piloto (a definir)  
**ID:** `condo-piloto-001`  
**Tipo:** Residencial  
**Características:**
- Tamaño pequeño-mediano (10-20 casas)
- Usuarios técnicamente capaces (para reportar issues)
- Flujo representativo de operación real

### Usuarios participantes
**Total:** 8 usuarios

| Rol | Cantidad | Access Level | Funciones |
|-----|----------|--------------|-----------|
| Admin Condominio | 1 | ADMIN_CONDOMINIO | Crear visitas, gestionar residentes |
| Personal Caseta | 1 | GUARDIA | Registrar entradas/salidas |
| Residentes | 6 | RESIDENTE | Ver sus propias visitas |

**Credenciales:** Generadas con password seguro, entregadas vía canal seguro

---

## 📋 ENDPOINTS CRÍTICOS (MIGRADOS)

Estos endpoints SÍ están migrados al patrón AUP y serán probados:

### ✅ Autenticación
- `POST /auth/login` - Login con JWT

### ✅ Visitas
- `POST /visitas/{condominio_id}` - Crear visita (Admin/Guardia)
- `GET /mis-visitas/{condominio_id}` - Ver mis visitas (Residente)
- `GET /visitas/condominio/{condominio_id}` - Listar todas (Admin/Guardia)

### ⚠️ Endpoints secundarios (NO tocar)
- Gestión de MSP
- Configuraciones avanzadas
- Features experimentales
- Admin global

---

## 🧪 ESCENARIOS DE PRUEBA

### Día 1 (Setup + Validación básica)

#### Escenario 1: Login y autenticación
- [ ] Admin puede hacer login
- [ ] Guardia puede hacer login
- [ ] 6 residentes pueden hacer login
- [ ] Token JWT se genera correctamente
- [ ] Token inválido es rechazado

#### Escenario 2: Aislamiento multi-tenant
- [ ] Usuario de condo-piloto-001 NO ve datos de otros condominios
- [ ] Intento de acceso a otro tenant retorna 403
- [ ] Logs muestran "ACCESO DENEGADO" para intentos inválidos

### Día 2 (Operación normal)

#### Escenario 3: Flujo de visitas
- [ ] Admin crea visita → éxito
- [ ] Guardia registra entrada → éxito
- [ ] Residente ve solo sus visitas → éxito
- [ ] Residente NO ve visitas de otros → éxito

#### Escenario 4: Validación de scope
- [ ] Residente intenta crear visita → 403
- [ ] Usuario sin scope intenta acceder → 403
- [ ] Scope LECTURA no puede modificar → 403

### Día 3 (Estabilidad + Edge cases)

#### Escenario 5: Carga moderada
- [ ] 50 requests/minuto sin errores
- [ ] Latencia p95 < 500ms
- [ ] No hay timeouts

#### Escenario 6: Manejo de errores
- [ ] Token expirado → 401 claro
- [ ] Sin scope → 403 claro
- [ ] Datos inválidos → 400 claro

---

## 📊 MÉTRICAS A OBSERVAR

### Métricas críticas (STOP si fallan)

| Métrica | Target | Comando verificación |
|---------|--------|----------------------|
| **Fugas multi-tenant** | 0 | `grep "tenant_id" logs.txt \| grep ERROR` |
| **RLS activo** | 100% | `grep "✅ RLS activado" logs.txt` |
| **Errores 500** | < 5 en 72h | `grep "500" logs.txt \| wc -l` |
| **Errores 403** | Solo legítimos | `grep "403" logs.txt` |

### Métricas de observación

| Métrica | Target | Acción si falla |
|---------|--------|-----------------|
| Latencia p95 | < 500ms | Investigar queries lentos |
| Tasa de error total | < 1% | Revisar logs |
| Uptime | 100% | Rollback si < 99% |

---

## 🚨 PLAN DE CONTINGENCIA

### Si aparece fuga multi-tenant
1. **STOP** piloto inmediato
2. Rollback a versión anterior
3. Revisar logs de aislamiento
4. Auditar `set_tenant_context()`
5. NO continuar hasta resolver

### Si > 10 errores 500 en 1 hora
1. Pausar nuevos usuarios
2. Revisar logs de stack traces
3. Identificar endpoint problemático
4. Hotfix o rollback
5. Reiniciar pruebas

### Si latencia > 2 segundos
1. Revisar queries sin índices
2. Verificar conexiones DB
3. Optimizar endpoint específico
4. Continuar si es aceptable

---

## 📝 REGISTRO DE ACTIVIDADES

### Template de log diario

```markdown
## Día X - [Fecha]

### Actividades
- [ ] Usuarios activos: X/8
- [ ] Requests procesados: ~XXX
- [ ] Errores detectados: X

### Incidentes
- Ninguno / [Descripción]

### Observaciones
- [Feedback usuarios]
- [Comportamiento sistema]
- [Ajustes realizados]

### Decisión
- ✅ Continuar / ⚠️ Pausar / ❌ Rollback
```

---

## ✅ CRITERIOS DE ÉXITO FINAL

Al finalizar 72h, el piloto es **EXITOSO** si:

- [ ] 0 fugas de datos entre tenants
- [ ] < 5 errores críticos (500)
- [ ] Latencia p95 < 500ms
- [ ] Usuarios pudieron operar normalmente
- [ ] RLS se activó en 100% de requests
- [ ] Logs son claros y grep-eables

**Decisión GO/NO-GO:**
- ✅ GO: Todos los criterios cumplidos → Continuar Fase 3
- ⚠️ PAUSAR: 1-2 criterios no cumplidos → Ajustar y repetir
- ❌ NO-GO: > 2 criterios no cumplidos → Volver a Fase 1

---

## 🔗 REFERENCIAS

- [PLAN_ACCION_IMPLEMENTACION.md](PLAN_ACCION_IMPLEMENTACION.md) - Plan completo
- [FASE6_PLAN_ALINEACION.md](FASE6_PLAN_ALINEACION.md) - Especificación técnica
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Guía de deployment

---

**Última actualización:** 2026-01-06  
**Responsable:** @B10sp4rt4n  
**Estado:** Pendiente de inicio
