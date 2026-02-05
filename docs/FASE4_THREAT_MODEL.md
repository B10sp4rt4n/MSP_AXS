# FASE 4: THREAT MODEL FORMAL — MSP_AXS

**Sistema:** MSP_AXS  
**Versión:** 4.0.0  
**Fecha:** 2026-01-01  
**Marco:** STRIDE (aplicado contextualmente)  
**Clasificación:** Análisis de Amenazas y Riesgos Residuales

---

## ALCANCE

Este documento analiza amenazas contra el sistema MSP_AXS considerando únicamente los controles ya implementados en FASE 1, 2 y 3.

**NO incluye:**
- Propuestas de mejora
- Controles externos (WAF, IDS, etc.)
- Amenazas de infraestructura (DDoS, hardware)
- Ingeniería social fuera del sistema

---

## RESUMEN EJECUTIVO

| Dominio | Amenazas | ALTO | MEDIO | BAJO | Aceptado |
|---------|----------|------|-------|------|----------|
| Identity | 5 | 1 | 2 | 1 | 1 |
| Scope | 6 | 1 | 3 | 1 | 1 |
| Authority | 5 | 0 | 2 | 2 | 1 |
| Policy | 4 | 1 | 2 | 0 | 1 |
| Event Sourcing | 6 | 1 | 2 | 2 | 1 |
| Boundary DB/App | 5 | 2 | 2 | 0 | 1 |
| Operación Humana | 4 | 0 | 2 | 1 | 1 |
| **TOTAL** | **35** | **6** | **15** | **7** | **7** |

---

## 1. DOMINIO: IDENTITY

### 1.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| ID-01 | Suplantación por robo de credenciales | password_hash con bcrypt | **MEDIO** | Aplicación |
| ID-02 | Suplantación por JWT robado | JWT con expiración (app) | **MEDIO** | Aplicación |
| ID-03 | Abuso de sesión activa | session_hash en eventos | **BAJO** | Aplicación |
| ID-04 | Confusión de identity_id entre usuarios | usuario_id único (PK) | **BAJO** | DB |
| ID-05 | Uso de campo `identity_label` para autorización | Documentación + linter CI | **ALTO** | Aplicación |

### 1.2 Análisis Detallado

#### ID-01: Suplantación por robo de credenciales

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Atacante obtiene email/password de usuario legítimo |
| **Vector** | Phishing, credential stuffing, fuerza bruta |
| **Mitigación existente** | `password_hash` usa bcrypt con salt |
| **Mitigación NO existente** | Rate limiting, MFA, detección de anomalías |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación (implementar controles adicionales) |

#### ID-02: Suplantación por JWT robado

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Atacante intercepta JWT válido y lo reutiliza |
| **Vector** | MITM, XSS, log leakage |
| **Mitigación existente** | JWT con expiración temporal (configurado en app) |
| **Mitigación NO existente** | Refresh token rotation, binding a IP/device |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación |

#### ID-03: Abuso de sesión activa

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Usuario legítimo abusa de sesión para acciones no autorizadas |
| **Vector** | Sesión válida usada fuera de contexto esperado |
| **Mitigación existente** | `session_hash` registrado en `events_aup` permite auditoría |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aplicación (validar contexto) |

#### ID-04: Confusión de identity_id entre usuarios

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Sistema confunde dos usuarios por ID similar |
| **Vector** | Bug de aplicación, colisión de ID |
| **Mitigación existente** | `usuario_id` es UNIQUE en DB |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

#### ID-05: Uso de `identity_label` para autorización

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Desarrollador usa `identity_label` (antes `rol`) para decidir permisos |
| **Vector** | Error de desarrollo, código legacy |
| **Mitigación existente** | Especificación FASE 1, linter CI, test de regresión |
| **Mitigación NO existente** | Enforcement en DB (campo es solo texto) |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Aplicación |

---

## 2. DOMINIO: SCOPE

### 2.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| SC-01 | Escalamiento lateral (acceso a otro tenant) | RLS en tablas operativas | **MEDIO** | DB + Aplicación |
| SC-02 | Escalamiento de access_level | Trigger de auditoría con alerta | **MEDIO** | DB (detecta) + App (previene) |
| SC-03 | Persistencia de scope revocado en cache | revoked_at + estado en DB | **MEDIO** | Aplicación |
| SC-04 | Confusión de tenant en request | RLS + validación app.tenant_id | **ALTO** | Aplicación |
| SC-05 | Scope sin expiración perpetuo | valida_hasta nullable | **BAJO** | Aceptado por diseño |
| SC-06 | Múltiples scopes activos simultáneos | Permitido por diseño | **BAJO** | Aceptado por diseño |

### 2.2 Análisis Detallado

#### SC-01: Escalamiento lateral

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Usuario accede a datos de tenant donde no tiene scope |
| **Vector** | Manipulación de tenant_id en request |
| **Mitigación existente** | RLS en visitas, evidencias, casetas, user_tenant_scope |
| **Mitigación parcial** | RLS depende de `SET app.tenant_id` correcto |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | DB (enforcement) + Aplicación (setear contexto) |

#### SC-02: Escalamiento de access_level

| Aspecto | Valor |
|---------|-------|
| **Descripción** | access_level modificado de `residente` a `msp_admin` |
| **Vector** | SQL directo, bug de aplicación |
| **Mitigación existente** | Trigger `trg_audit_user_tenant_scope` registra cambio con `resultado = 'alerta'` |
| **Mitigación NO existente** | Bloqueo preventivo de escalamiento |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | DB (detecta) + Aplicación (previene) |

#### SC-03: Persistencia de scope revocado en cache

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Aplicación cachea scope y no detecta revocación |
| **Vector** | Cache de aplicación sin invalidación |
| **Mitigación existente** | `revoked_at` y `estado` en DB son fuente de verdad |
| **Mitigación NO existente** | Invalidación activa de cache |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación |

#### SC-04: Confusión de tenant en request

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Request enviado con tenant_id incorrecto para el usuario |
| **Vector** | Bug de frontend, manipulación de API |
| **Mitigación existente** | RLS filtra por `app.tenant_id` |
| **Mitigación NO existente** | Validación de que usuario tiene scope en tenant del request |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Aplicación (validar scope antes de operar) |

#### SC-05: Scope sin expiración

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Scope con `valida_hasta = NULL` permanece activo indefinidamente |
| **Vector** | Diseño del sistema |
| **Mitigación existente** | Ninguna (por diseño) |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aceptado por diseño |

#### SC-06: Múltiples scopes activos

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Usuario con scopes en múltiples tenants simultáneamente |
| **Vector** | Diseño multi-tenant |
| **Mitigación existente** | Cada operación requiere tenant_id explícito |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aceptado por diseño |

---

## 3. DOMINIO: AUTHORITY

### 3.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| AU-01 | Escalamiento vertical (obtener authority sin otorgamiento) | authorities_gov es tabla separada | **BAJO** | DB + Aplicación |
| AU-02 | Reactivación indebida de authority revocada | Trigger `trg_block_reactivation_authority` | **BAJO** | DB |
| AU-03 | Revocación incompleta (authority revocada pero efectiva) | `estado` + `revoked_at` consultados en tiempo real | **MEDIO** | Aplicación |
| AU-04 | Authority global sin restricción | Diseño: authority global es omnipotente | **MEDIO** | Aceptado por diseño |
| AU-05 | Eliminación física de authority sin rastro | Trigger audita DELETE con alerta | **BAJO** | DB |

### 3.2 Análisis Detallado

#### AU-01: Escalamiento vertical

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Usuario obtiene authority sin otorgamiento legítimo |
| **Vector** | SQL injection, bug de aplicación |
| **Mitigación existente** | `authorities_gov` es tabla separada, INSERT requiere acceso explícito |
| **Mitigación adicional** | Trigger audita toda creación |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB + Aplicación |

#### AU-02: Reactivación indebida

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Authority revocada es reactivada sin autorización |
| **Vector** | SQL directo |
| **Mitigación existente** | `trg_block_reactivation_authority` requiere flag `reactivation_authorized` |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

#### AU-03: Revocación incompleta

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Authority revocada en DB pero aplicación no lo detecta |
| **Vector** | Cache de aplicación, race condition |
| **Mitigación existente** | Consulta a DB en tiempo real (sin cache recomendado) |
| **Mitigación NO existente** | Invalidación activa |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación |

#### AU-04: Authority global sin restricción

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Authority `tipo = 'global'` puede hacer todo en plataforma |
| **Vector** | Diseño del sistema |
| **Mitigación existente** | Solo usuarios bootstrapped tienen authority global |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aceptado por diseño (root es omnipotente) |

#### AU-05: Eliminación física sin rastro

| Aspecto | Valor |
|---------|-------|
| **Descripción** | DELETE de authority sin auditoría |
| **Vector** | SQL directo con bypass |
| **Mitigación existente** | Trigger `trg_audit_authorities_gov` registra DELETE con `resultado = 'alerta'` |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

---

## 4. DOMINIO: POLICY

### 4.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| PO-01 | Bypass de límites de política | Ninguno en DB | **ALTO** | Aplicación |
| PO-02 | Ambigüedad de interpretación de `limites` JSON | Schema no validado | **MEDIO** | Aplicación |
| PO-03 | Política expirada no detectada | `valida_hasta` consultado en app | **MEDIO** | Aplicación |
| PO-04 | Ausencia de política = permitido | Diseño: default deny en app | **BAJO** | Aceptado por diseño |

### 4.2 Análisis Detallado

#### PO-01: Bypass de límites

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Operación excede límite de política pero se ejecuta |
| **Vector** | Aplicación no consulta `policies_gov` antes de operar |
| **Mitigación existente** | Ninguna en DB (enforcement es en aplicación) |
| **Mitigación NO existente** | CHECK constraints o triggers que validen límites |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Aplicación |

#### PO-02: Ambigüedad de `limites`

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Campo `limites` JSONB sin schema definido |
| **Vector** | Diferentes interpretaciones de estructura JSON |
| **Mitigación existente** | Documentación de estructura esperada |
| **Mitigación NO existente** | JSON Schema validation en DB o app |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación |

#### PO-03: Política expirada no detectada

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Política con `valida_hasta` pasado sigue siendo usada |
| **Vector** | Aplicación no valida vigencia |
| **Mitigación existente** | `valida_hasta` está en DB, app debe consultarlo |
| **Mitigación NO existente** | Job de expiración automática |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación |

#### PO-04: Ausencia de política = permitido

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Si no existe política para acción, ¿se permite o deniega? |
| **Vector** | Omisión de configuración |
| **Mitigación existente** | Documentación AUP: "default deny" |
| **Mitigación NO existente** | Enforcement automático en DB |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aceptado por diseño (app implementa default deny) |

---

## 5. DOMINIO: EVENT SOURCING (events_aup)

### 5.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| EV-01 | Omisión de evento crítico | Triggers en authorities/scopes | **MEDIO** | Aplicación (para otros eventos) |
| EV-02 | Manipulación de evento existente | Trigger bloquea UPDATE | **BAJO** | DB |
| EV-03 | Eliminación de evento | Trigger bloquea DELETE | **BAJO** | DB |
| EV-04 | Reordenamiento de eventos | Orden por (timestamp, event_id) | **BAJO** | DB |
| EV-05 | Colisión de hash_evento | Enmienda v3.0.1: event_id en hash | **BAJO** | DB |
| EV-06 | Corrupción de events_aup por superuser | Ninguna | **ALTO** | Operación |

### 5.2 Análisis Detallado

#### EV-01: Omisión de evento crítico

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Operación crítica se ejecuta sin generar evento |
| **Vector** | Bug de aplicación, bypass de trigger |
| **Mitigación existente** | Triggers en `authorities_gov` y `user_tenant_scope` |
| **Mitigación parcial** | Otras entidades dependen de aplicación |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Aplicación (para eventos no cubiertos por triggers) |

#### EV-02: Manipulación de evento

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Evento existente es modificado post-inserción |
| **Vector** | SQL directo |
| **Mitigación existente** | `trg_protect_events_immutability` bloquea UPDATE |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

#### EV-03: Eliminación de evento

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Evento eliminado para ocultar acción |
| **Vector** | SQL directo |
| **Mitigación existente** | `trg_protect_events_immutability` bloquea DELETE |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

#### EV-04: Reordenamiento

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Eventos procesados en orden incorrecto |
| **Vector** | Query sin ORDER BY correcto |
| **Mitigación existente** | Especificación: `ORDER BY timestamp ASC, event_id ASC` |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB (índices) + Aplicación (queries) |

#### EV-05: Colisión de hash

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Dos eventos generan mismo hash_evento |
| **Vector** | Eventos idénticos en mismo timestamp |
| **Mitigación existente** | Enmienda v3.0.1: `event_id` incluido en cálculo de hash |
| **Riesgo residual** | **BAJO** |
| **Responsable** | DB |

#### EV-06: Corrupción por superuser

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Usuario con privilegios de superuser modifica events_aup |
| **Vector** | Acceso administrativo a PostgreSQL |
| **Mitigación existente** | Ninguna (superuser puede disable triggers) |
| **Mitigación externa** | Backups, checksums externos (fuera de alcance) |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Operación |

---

## 6. DOMINIO: BOUNDARY DB / APLICACIÓN

### 6.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| BD-01 | app.tenant_id no seteado | RLS falla silenciosamente | **ALTO** | Aplicación |
| BD-02 | app.tenant_id manipulado | Ninguna validación en DB | **ALTO** | Aplicación |
| BD-03 | Acceso SQL directo por desarrollador | Rol admin_bypass existe | **MEDIO** | Operación |
| BD-04 | Conexión con rol incorrecto | Roles app_user vs admin_bypass | **MEDIO** | Operación |
| BD-05 | FKs no enforced entre dominios | Referencias por ID string | **BAJO** | Aceptado por diseño |

### 6.2 Análisis Detallado

#### BD-01: app.tenant_id no seteado

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Aplicación no ejecuta `SET app.tenant_id` antes de query |
| **Vector** | Bug de middleware, omisión de configuración |
| **Mitigación existente** | `current_setting('app.tenant_id', true)` retorna NULL → RLS no filtra correctamente |
| **Comportamiento** | Query puede retornar datos incorrectos o vacíos |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Aplicación |

#### BD-02: app.tenant_id manipulado

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Atacante logra que aplicación setee tenant_id incorrecto |
| **Vector** | Inyección en header, parameter tampering |
| **Mitigación existente** | Ninguna en DB (confianza en aplicación) |
| **Riesgo residual** | **ALTO** |
| **Responsable** | Aplicación (validar contra JWT/sesión) |

#### BD-03: Acceso SQL directo

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Desarrollador ejecuta SQL sin pasar por aplicación |
| **Vector** | Acceso a consola de DB |
| **Mitigación existente** | Rol `admin_bypass` separado con BYPASSRLS |
| **Mitigación adicional** | Triggers auditan cambios en tablas críticas |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Operación (control de acceso a DB) |

#### BD-04: Conexión con rol incorrecto

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Aplicación conecta con `admin_bypass` en lugar de `app_user` |
| **Vector** | Misconfiguration de connection string |
| **Mitigación existente** | Documentación de roles |
| **Mitigación NO existente** | Alertas de uso de admin_bypass |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Operación |

#### BD-05: FKs no enforced entre dominios

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Referencias entre aup_core, aup_event, aup_gov por ID string sin FK |
| **Vector** | Datos huérfanos, inconsistencias |
| **Mitigación existente** | IDs hardcodeados en bootstrap, validación en app |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aceptado por diseño (bases separadas) |

---

## 7. DOMINIO: OPERACIÓN HUMANA

### 7.1 Tabla de Amenazas

| ID | Amenaza | Mitigación Existente | Riesgo | Responsable |
|----|---------|---------------------|--------|-------------|
| OP-01 | Error administrativo (revocación accidental) | Trigger de auditoría registra | **MEDIO** | Operación |
| OP-02 | Uso legítimo indebido (admin abusa poder) | Events_aup registra acciones | **MEDIO** | Operación |
| OP-03 | Admin override consciente | Flag reactivation_authorized | **BAJO** | Aceptado por diseño |
| OP-04 | Pérdida de credentials de root | Ninguna recuperación definida | **BAJO** | Operación |

### 7.2 Análisis Detallado

#### OP-01: Error administrativo

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Admin revoca authority o scope por error |
| **Vector** | Error humano en consola o UI |
| **Mitigación existente** | `events_aup` registra toda revocación con identity_id del actor |
| **Mitigación adicional** | Reactivación posible con flag explícito |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Operación |

#### OP-02: Uso legítimo indebido

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Admin con authority legítima abusa de su poder |
| **Vector** | Insider threat |
| **Mitigación existente** | `events_aup` registra todas las acciones del admin |
| **Mitigación NO existente** | Segregación de duties, aprobación dual |
| **Riesgo residual** | **MEDIO** |
| **Responsable** | Operación (políticas de empresa) |

#### OP-03: Admin override consciente

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Admin reactiva authority revocada usando flag autorizado |
| **Vector** | Uso legítimo del sistema |
| **Mitigación existente** | Flag `reactivation_authorized` + evento en auditoría |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Aceptado por diseño (override intencional documentado) |

#### OP-04: Pérdida de credentials de root

| Aspecto | Valor |
|---------|-------|
| **Descripción** | Password de usuario root olvidado |
| **Vector** | Rotación de personal, negligencia |
| **Mitigación existente** | Ninguna (no hay recovery flow definido) |
| **Mitigación externa** | Acceso directo a DB para reset (requiere admin_bypass) |
| **Riesgo residual** | **BAJO** |
| **Responsable** | Operación |

---

## 8. MATRIZ DE RIESGOS CONSOLIDADA

### 8.1 Riesgos ALTOS (requieren atención prioritaria)

| ID | Amenaza | Dominio | Responsable |
|----|---------|---------|-------------|
| ID-05 | Uso de identity_label para autorización | Identity | Aplicación |
| SC-04 | Confusión de tenant en request | Scope | Aplicación |
| PO-01 | Bypass de límites de política | Policy | Aplicación |
| EV-06 | Corrupción de events_aup por superuser | Event Sourcing | Operación |
| BD-01 | app.tenant_id no seteado | Boundary | Aplicación |
| BD-02 | app.tenant_id manipulado | Boundary | Aplicación |

### 8.2 Riesgos MEDIOS (monitorear)

| ID | Amenaza | Dominio | Responsable |
|----|---------|---------|-------------|
| ID-01 | Suplantación por robo de credenciales | Identity | Aplicación |
| ID-02 | Suplantación por JWT robado | Identity | Aplicación |
| SC-01 | Escalamiento lateral | Scope | DB + Aplicación |
| SC-02 | Escalamiento de access_level | Scope | DB + Aplicación |
| SC-03 | Persistencia de scope revocado en cache | Scope | Aplicación |
| AU-03 | Revocación incompleta | Authority | Aplicación |
| AU-04 | Authority global sin restricción | Authority | Aceptado |
| PO-02 | Ambigüedad de `limites` JSON | Policy | Aplicación |
| PO-03 | Política expirada no detectada | Policy | Aplicación |
| EV-01 | Omisión de evento crítico | Event Sourcing | Aplicación |
| BD-03 | Acceso SQL directo | Boundary | Operación |
| BD-04 | Conexión con rol incorrecto | Boundary | Operación |
| OP-01 | Error administrativo | Operación | Operación |
| OP-02 | Uso legítimo indebido | Operación | Operación |

### 8.3 Riesgos BAJOS (aceptables)

| ID | Amenaza | Dominio | Responsable |
|----|---------|---------|-------------|
| ID-03 | Abuso de sesión activa | Identity | Aplicación |
| ID-04 | Confusión de identity_id | Identity | DB |
| SC-05 | Scope sin expiración | Scope | Aceptado |
| AU-01 | Escalamiento vertical | Authority | DB + App |
| AU-02 | Reactivación indebida | Authority | DB |
| AU-05 | Eliminación física sin rastro | Authority | DB |
| EV-02 | Manipulación de evento | Event Sourcing | DB |
| EV-03 | Eliminación de evento | Event Sourcing | DB |
| EV-04 | Reordenamiento | Event Sourcing | DB |
| EV-05 | Colisión de hash | Event Sourcing | DB |
| BD-05 | FKs no enforced | Boundary | Aceptado |
| OP-03 | Admin override | Operación | Aceptado |
| OP-04 | Pérdida de credentials | Operación | Operación |

### 8.4 Riesgos Aceptados por Diseño

| ID | Amenaza | Justificación |
|----|---------|---------------|
| SC-05 | Scope sin expiración | Scopes permanentes son caso de uso válido |
| SC-06 | Múltiples scopes activos | Diseño multi-tenant lo requiere |
| AU-04 | Authority global omnipotente | Root necesita poder total |
| PO-04 | Ausencia de política = deny | Default deny implementado en app |
| BD-05 | FKs no enforced | Bases separadas por dominio AUP |
| OP-03 | Admin override | Mecanismo controlado con auditoría |
| EV-06 | Superuser puede manipular | Límite de confianza del sistema |

---

## 9. LÍMITES DE CONFIANZA

### 9.1 Diagrama de Límites

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ZONA DE CONFIANZA                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     PostgreSQL (Neon)                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │  aup_core   │  │  aup_event  │  │   aup_gov   │          │   │
│  │  │   (RLS)     │  │  (APPEND)   │  │  (TRIGGERS) │          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  │                           │                                   │   │
│  │                    ══════════════                            │   │
│  │                    LÍMITE: DB/App                            │   │
│  │                    ══════════════                            │   │
│  │                           │                                   │   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │              APLICACIÓN (FastAPI)                    │    │   │
│  │  │  - Valida JWT                                        │    │   │
│  │  │  - Setea app.tenant_id                               │    │   │
│  │  │  - Consulta authorities/policies                     │    │   │
│  │  │  - Emite eventos                                     │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                       ══════════════                               │
│                       LÍMITE: App/Usuario                          │
│                       ══════════════                               │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                    ┌──────────────────────┐
                    │   ZONA NO CONFIABLE  │
                    │  - Usuarios finales  │
                    │  - Requests HTTP     │
                    │  - JWTs presentados  │
                    └──────────────────────┘
```

### 9.2 Responsabilidades por Zona

| Zona | Responsabilidad | Lo que NO hace |
|------|-----------------|----------------|
| **DB** | Enforce RLS, triggers, inmutabilidad | Autorización de negocio |
| **Aplicación** | Autenticación, autorización, emisión eventos | Inmutabilidad (depende de DB) |
| **Operación** | Control de acceso a DB, backups | Validación de lógica |

---

## 10. CONCLUSIÓN

### 10.1 Estado del Sistema

| Aspecto | Estado |
|---------|--------|
| **Autenticación** | Implementada (bcrypt + JWT) |
| **Autorización** | Delegada a aplicación (authorities + policies) |
| **Aislamiento de tenant** | Parcial (RLS en tablas operativas) |
| **Auditoría** | Fuerte (triggers + events_aup inmutable) |
| **Reconstrucción histórica** | Posible (event sourcing) |

### 10.2 Dependencias Críticas de la Aplicación

El sistema **REQUIERE** que la aplicación:

1. Setee `app.tenant_id` correctamente en cada request
2. Valide `app.tenant_id` contra JWT/sesión del usuario
3. Consulte `authorities_gov` antes de operaciones de gobierno
4. Consulte `policies_gov` antes de aplicar límites
5. NO use `identity_label` para decisiones de autorización
6. NO cachee scopes/authorities sin invalidación
7. Emita eventos para operaciones no cubiertas por triggers

### 10.3 Lo que el Sistema NO Garantiza

- Protección contra superuser malicioso
- Validación de schema de JSON en políticas
- Rate limiting / protección contra fuerza bruta
- MFA / autenticación fuerte
- Segregación de duties administrativas
- Recovery automático de credentials

---

**FIN DE THREAT MODEL — FASE 4**
