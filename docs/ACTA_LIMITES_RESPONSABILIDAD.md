# ACTA DE LÍMITES Y RESPONSABILIDAD DEL SISTEMA MSP_AXS

**Versión:** 1.0.0  
**Fecha:** 2026-01-01  
**Tipo:** Documento Fundacional  
**Estado:** Cerrado

---

## 1. PROPÓSITO DEL ACTA

### 1.1 Por qué Existe Este Documento

Este acta establece de forma explícita y no negociable:

- Los límites técnicos del sistema MSP_AXS
- Las responsabilidades de cada dominio (DB, aplicación, operación)
- Los riesgos que se aceptan conscientemente por diseño
- Los escenarios que no constituyen fallos del sistema

### 1.2 Qué Problema Previene

Este documento previene:

| Problema | Cómo lo Previene |
|----------|------------------|
| Expectativas desalineadas | Define qué hace y qué no hace el sistema |
| Atribución incorrecta de responsabilidad | Asigna responsables por dominio |
| Demandas por fallos que no son fallos | Documenta riesgos aceptados |
| Uso del sistema fuera de su alcance | Declara límites explícitos |
| Confusión en análisis post-incidente | Establece criterios de clasificación |

### 1.3 Alcance de Aplicación

Este acta aplica a:

- Toda instancia de MSP_AXS en producción
- Toda evaluación de incidentes de seguridad
- Toda auditoría interna o externa
- Todo análisis de responsabilidad post-incidente

---

## 2. PRINCIPIOS FUNDACIONALES DEL SISTEMA

### 2.1 Principio de No Omnisciencia

**Qué significa:**  
El sistema registra y protege únicamente aquello que pasa a través de sus interfaces definidas. No tiene visibilidad sobre acciones que ocurren fuera de su perímetro.

**Qué NO significa:**  
- Que el sistema detecte acciones realizadas directamente en la base de datos por superusuarios
- Que el sistema identifique ataques de red o compromiso de infraestructura
- Que el sistema infiera intenciones no expresadas en operaciones

**Ejemplo aplicado a MSP_AXS:**  
Si un operador con acceso de superusuario desactiva triggers y modifica directamente la tabla `events_aup`, el sistema no tiene forma de detectarlo ni registrarlo. Esto no es un fallo del sistema; es un escenario fuera de su perímetro de visibilidad.

---

### 2.2 Principio de Contexto Correcto

**Qué significa:**  
El sistema opera correctamente si y solo si recibe el contexto correcto de la aplicación. La responsabilidad de configurar ese contexto es de la aplicación, no del sistema.

**Qué NO significa:**  
- Que el sistema valide si `app.tenant_id` corresponde al usuario autenticado
- Que el sistema compense errores de configuración de la aplicación
- Que el sistema detecte contextos maliciosamente incorrectos

**Ejemplo aplicado a MSP_AXS:**  
Si la aplicación configura `SET app.tenant_id = 'tenant_A'` pero el usuario autenticado solo tiene scope en `tenant_B`, las políticas RLS filtrarán por `tenant_A`. El resultado puede ser vacío o incorrecto. Esto no es un fallo del sistema; es un fallo de configuración de la aplicación.

---

### 2.3 Principio de Separación entre Registro y Prevención

**Qué significa:**  
El sistema distingue entre:
- **Registrar:** Documentar que algo ocurrió (auditoría)
- **Prevenir:** Impedir que algo ocurra (control de acceso)

No todo lo que se registra se previene. No todo lo que se previene se registra.

**Qué NO significa:**  
- Que registrar un evento implique que se bloqueó la acción
- Que la ausencia de registro implique que la acción fue permitida
- Que el sistema deba prevenir todo lo que detecta

**Ejemplo aplicado a MSP_AXS:**  
El trigger `trg_audit_user_tenant_scope` registra cambios de `access_level` con `resultado = 'alerta'`. Esto significa que el cambio **ocurrió** y **se registró**, no que fue **bloqueado**. La prevención es responsabilidad de la aplicación antes de ejecutar la operación.

---

### 2.4 Principio de Autoridad Humana Final

**Qué significa:**  
El sistema no reemplaza decisiones humanas. Provee mecanismos para que humanos autorizados ejecuten operaciones extraordinarias (como reactivaciones) de forma controlada y auditable.

**Qué NO significa:**  
- Que el sistema bloquee indefinidamente operaciones legítimas
- Que la existencia de un flag de override sea una vulnerabilidad
- Que el sistema deba impedir que administradores administren

**Ejemplo aplicado a MSP_AXS:**  
El trigger `trg_block_reactivation_authority` bloquea reactivaciones de autoridades revocadas **a menos que** se configure el flag `reactivation_authorized`. Esta excepción existe por diseño para permitir operaciones legítimas extraordinarias. El uso de este flag queda registrado en `events_aup`.

---

### 2.5 Principio de Riesgo Aceptado

**Qué significa:**  
Existen riesgos que el sistema conoce, documenta y acepta conscientemente porque:
- Mitigarlos implicaría complejidad desproporcionada
- Son inherentes al modelo de confianza elegido
- Representan casos de uso legítimos

**Qué NO significa:**  
- Que estos riesgos sean desconocidos
- Que puedan reclamarse como defectos
- Que deban mitigarse en versiones futuras

**Ejemplo aplicado a MSP_AXS:**  
Un scope con `valida_hasta = NULL` permanece activo indefinidamente. Esto es un riesgo aceptado porque representa un caso de uso válido (acceso permanente de propietarios). No es un bug ni una omisión.

---

### 2.6 Principio de Uso Responsable

**Qué significa:**  
El sistema provee herramientas. El uso correcto de esas herramientas es responsabilidad del operador. El sistema no compensa uso negligente, malicioso o incompetente por parte de usuarios autorizados.

**Qué NO significa:**  
- Que el sistema deba detectar uso indebido por usuarios legítimos
- Que el sistema deba prevenir errores de administradores
- Que el sistema sea responsable de decisiones humanas

**Ejemplo aplicado a MSP_AXS:**  
Si un administrador con autoridad legítima revoca el scope de todos los usuarios de un tenant, el sistema registrará cada revocación. No bloqueará la operación ni alertará sobre el volumen. El administrador tenía autoridad; la decisión fue suya.

---

## 3. LÍMITES TÉCNICOS EXPLÍCITOS

### 3.1 Qué el Sistema NO Intenta Proteger

| Escenario | Razón de Exclusión |
|-----------|-------------------|
| Compromiso de servidor de base de datos | Límite de confianza |
| Ataques de red (MITM, DDoS, sniffing) | Responsabilidad de infraestructura |
| Vulnerabilidades de aplicación (SQLi, XSS) | Responsabilidad de aplicación |
| Robo de credenciales fuera del sistema | Fuera de perímetro |
| Ingeniería social contra usuarios | No mitigable técnicamente |
| Insider threat con privilegios de superusuario | Límite de confianza aceptado |
| Configuración incorrecta de infraestructura | Responsabilidad operativa |

### 3.2 Qué Ataques Quedan Fuera de Alcance

| Tipo de Ataque | Estado |
|----------------|--------|
| Fuerza bruta contra autenticación | Fuera de alcance (requiere rate limiting en app) |
| Inyección SQL | Fuera de alcance (requiere queries parametrizados) |
| Robo de JWT | Fuera de alcance (requiere protección de transporte) |
| Manipulación de eventos por superusuario | Fuera de alcance (límite de confianza) |
| Exfiltración de datos vía backup | Fuera de alcance (responsabilidad operativa) |
| Correlación de metadatos entre tenants | Fuera de alcance (no implementado) |

### 3.3 Qué Escenarios NO Constituyen un Bug

| Escenario | Clasificación |
|-----------|---------------|
| RLS no filtra porque `app.tenant_id` no fue seteado | Fallo de configuración |
| Usuario accede a datos de tenant donde no tiene scope pero la app no validó | Fallo de aplicación |
| Evento no registrado porque la app no llamó a la función de auditoría | Fallo de aplicación |
| Política no aplicada porque la app no consultó `policies_gov` | Fallo de aplicación |
| Autoridad revocada pero cacheada en app | Fallo de aplicación |
| Trigger desactivado por superusuario | Operación fuera de perímetro |
| Datos modificados directamente en DB | Operación fuera de perímetro |

---

## 4. RESPONSABILIDAD POR DOMINIO

### 4.1 Responsabilidades de la Base de Datos

La base de datos **es responsable de:**

| Responsabilidad | Mecanismo |
|-----------------|-----------|
| Filtrar datos por tenant cuando `app.tenant_id` está configurado | RLS policies |
| Bloquear UPDATE/DELETE en `events_aup` | Trigger de inmutabilidad |
| Registrar cambios en `authorities_gov` | Trigger de auditoría |
| Registrar cambios en `user_tenant_scope` | Trigger de auditoría |
| Bloquear reactivaciones no autorizadas | Trigger de bloqueo |
| Almacenar passwords hasheados | Campo `password_hash` |

La base de datos **NO es responsable de:**

| Escenario | Responsable Real |
|-----------|------------------|
| Validar que `app.tenant_id` corresponda al usuario | Aplicación |
| Decidir si una operación está autorizada | Aplicación |
| Detectar patrones de abuso | Aplicación / Operación |
| Prevenir rate limiting | Aplicación |
| Validar estructura de JSON en políticas | Aplicación |

### 4.2 Responsabilidades de la Aplicación

La aplicación **es responsable de:**

| Responsabilidad | Consecuencia si Falla |
|-----------------|----------------------|
| Autenticar usuarios correctamente | Suplantación de identidad |
| Configurar `app.tenant_id` en cada request | Bypass de RLS |
| Validar que usuario tiene scope en tenant solicitado | Acceso cruzado |
| Consultar `authorities_gov` antes de operar | Acciones sin permiso |
| Consultar `policies_gov` antes de aplicar límites | Límites no enforced |
| Emitir eventos para operaciones no cubiertas por triggers | Gaps en auditoría |
| No cachear permisos sin invalidación | Permisos obsoletos activos |
| Sanitizar inputs | Inyección SQL |
| Proteger JWT en tránsito | Robo de sesión |

### 4.3 Responsabilidades de Operación / Cliente

El operador **es responsable de:**

| Responsabilidad | Impacto si Falla |
|-----------------|------------------|
| Controlar acceso a credenciales de superusuario | Compromiso total |
| No desactivar triggers en producción | Pérdida de auditoría e inmutabilidad |
| Mantener backups cifrados | Exposición de datos históricos |
| Monitorear eventos con `resultado = 'alerta'` | Incidentes no detectados |
| Revisar periódicamente scopes y autoridades | Privilegios acumulados |
| Rotar credenciales de servicio | Exposición prolongada |
| No usar rol `admin_bypass` para operación normal | Bypass de RLS |

### 4.4 Responsabilidades de Infraestructura

La infraestructura subyacente **es responsable de:**

| Responsabilidad | Fuera de Control de MSP_AXS |
|-----------------|----------------------------|
| Cifrado en tránsito (TLS) | Sí |
| Cifrado en reposo | Sí |
| Protección contra DDoS | Sí |
| Disponibilidad de red | Sí |
| Seguridad física de servidores | Sí |
| Gestión de certificados | Sí |

---

## 5. ESCENARIOS DE FRONTERA

### 5.1 Tabla de Escenarios Ambiguos

| Escenario | ¿Es Fallo del Sistema? | Clasificación Real |
|-----------|------------------------|-------------------|
| Usuario con scope revocado sigue accediendo porque la app cachea | NO | Fallo de aplicación |
| RLS no filtra porque la conexión usa rol `admin_bypass` | NO | Fallo operativo |
| Evento crítico no registrado porque no hay trigger para esa tabla | NO | Limitación conocida |
| Dos eventos con mismo timestamp tienen orden incorrecto | NO | Aplicación debe usar ORDER BY correcto |
| Admin legítimo elimina datos masivamente | NO | Uso autorizado (aunque destructivo) |
| Política JSON mal formada causa error en app | NO | Fallo de aplicación (validar JSON) |
| Usuario obtiene authority porque app no consultó | NO | Fallo de aplicación |
| Trigger desactivado por DBA durante mantenimiento | NO | Operación fuera de perímetro |
| Password débil permite acceso por fuerza bruta | NO | Fallo de aplicación (sin rate limiting) |
| JWT robado usado desde otra IP | NO | Fallo de aplicación (sin binding) |

### 5.2 Criterios de Clasificación

Para determinar si un incidente es fallo del sistema:

| Pregunta | Si la Respuesta es NO |
|----------|----------------------|
| ¿El sistema recibió el contexto correcto? | Fallo de configuración |
| ¿El sistema fue usado a través de sus interfaces definidas? | Operación fuera de perímetro |
| ¿El sistema tenía visibilidad sobre la operación? | Límite de perímetro |
| ¿El comportamiento contradice la documentación? | Posible bug real |
| ¿El sistema tenía control sobre el componente que falló? | Fallo de otro dominio |

### 5.3 Escenarios que SÍ Constituyen Fallo del Sistema

| Escenario | Por qué es Fallo Real |
|-----------|----------------------|
| Trigger activo no registra evento | Contradice especificación |
| RLS no filtra con `app.tenant_id` correctamente configurado | Bug de política |
| `events_aup` permite UPDATE con rol `app_user` | Trigger defectuoso |
| Hash de evento no coincide con recalculación | Corrupción o bug |
| Bloqueo de reactivación no funciona sin flag | Trigger defectuoso |

---

## 6. RELACIÓN CON EL SECURITY POSTURE

### 6.1 Complementariedad

| Documento | Responde a |
|-----------|------------|
| Security Posture (FASE 5) | ¿Qué protege el sistema? ¿Cómo? |
| Acta de Límites (Este documento) | ¿Hasta dónde? ¿Qué no es su culpa? |

Estos documentos no se contradicen. Se complementan:

- El Security Posture describe **capacidades**
- El Acta de Límites describe **fronteras**

### 6.2 Uso Conjunto

| Decisión | Documento a Consultar |
|----------|----------------------|
| ¿MSP_AXS es adecuado para mi caso de uso? | Security Posture |
| ¿Este incidente es responsabilidad del sistema? | Acta de Límites |
| ¿Qué controles existen? | Security Posture |
| ¿Qué riesgos acepto al usar el sistema? | Acta de Límites |
| ¿Qué debe hacer mi aplicación? | Ambos |

### 6.3 Precedencia

En caso de ambigüedad interpretativa:

1. El Acta de Límites tiene precedencia sobre interpretaciones expansivas del Security Posture
2. Los Principios Fundacionales (Sección 2) tienen precedencia sobre ejemplos específicos
3. La clasificación de Escenarios de Frontera (Sección 5) es definitiva para esos casos

---

## 7. DECLARACIÓN DE CIERRE

### 7.1 Alcance Real del Sistema

MSP_AXS es un sistema de control de acceso para entornos residenciales multi-tenant que:

- Aísla datos entre tenants mediante RLS
- Registra decisiones críticas de gobierno de forma inmutable
- Provee alertas sobre cambios de privilegios
- Separa identidad, alcance, autoridad y política
- Depende de configuración correcta por la aplicación
- Depende de operación responsable por el cliente
- Opera dentro de un perímetro de confianza definido

### 7.2 Lo que MSP_AXS NO Es

MSP_AXS **no es:**

- Un sistema de detección de intrusiones
- Una solución de seguridad perimetral
- Un sustituto de buenas prácticas de desarrollo
- Un compensador de errores de configuración
- Una garantía contra atacantes con acceso privilegiado
- Un sistema certificado para entornos regulados específicos

### 7.3 Invitación a NO Usar MSP_AXS Fuera de Estos Límites

Si su caso de uso requiere:

| Requisito | MSP_AXS NO es Adecuado |
|-----------|------------------------|
| Certificaciones formales (ISO, SOC, PCI) | ✗ |
| Protección contra superusuarios maliciosos | ✗ |
| Detección automática de anomalías | ✗ |
| MFA obligatorio | ✗ |
| Cifrado en reposo gestionado | ✗ |
| Segregación de duties con aprobación dual | ✗ |
| Rate limiting en capa de datos | ✗ |

**No use MSP_AXS para estos escenarios.** El sistema no fue diseñado para ellos y usarlo fuera de sus límites documentados transfiere toda responsabilidad al operador.

### 7.4 Aceptación Implícita

El uso de MSP_AXS en producción implica aceptación de:

1. Los Principios Fundacionales descritos en la Sección 2
2. Los Límites Técnicos descritos en la Sección 3
3. La distribución de Responsabilidades descrita en la Sección 4
4. Los Riesgos Aceptados documentados en FASE 4 (Threat Model)
5. Las limitaciones declaradas en FASE 5 (Security Posture)

---

## ANEXO: CHECKLIST DE VERIFICACIÓN PRE-PRODUCCIÓN

Antes de usar MSP_AXS en producción, el operador debe confirmar:

| # | Verificación | Responsable |
|---|--------------|-------------|
| 1 | La aplicación configura `app.tenant_id` en cada request | Aplicación |
| 2 | La aplicación valida `tenant_id` contra JWT/sesión | Aplicación |
| 3 | La aplicación consulta `authorities_gov` antes de operar | Aplicación |
| 4 | La aplicación NO cachea permisos sin invalidación | Aplicación |
| 5 | La aplicación NO usa `identity_label` para autorizar | Aplicación |
| 6 | El rol de conexión es `app_user`, no `admin_bypass` | Operación |
| 7 | Triggers están activos en producción | Operación |
| 8 | Existe monitoreo de eventos con `resultado = 'alerta'` | Operación |
| 9 | Credenciales de superusuario están restringidas | Operación |
| 10 | Existe proceso de revisión periódica de scopes | Operación |

---

**FIN DEL ACTA — LÍMITES Y RESPONSABILIDAD v1.0.0**
