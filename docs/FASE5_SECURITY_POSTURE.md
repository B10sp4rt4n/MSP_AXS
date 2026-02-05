# MSP_AXS — Security Posture Document

**Versión:** 1.0.0  
**Fecha:** 2026-01-01  
**Clasificación:** Documento Técnico para Evaluación de Seguridad  
**Audiencia:** Auditores externos, CISO, CTO, equipos de compliance

---

## 1. RESUMEN EJECUTIVO

### 1.1 Qué es MSP_AXS

MSP_AXS es una plataforma de control de acceso para entornos residenciales administrados (condominios, fraccionamientos, comunidades cerradas). Permite:

- Registro y validación de visitantes
- Generación de códigos QR para acceso
- Gestión de pre-registros por residentes
- Captura de evidencias (fotografías de identificación)
- Administración multi-condominio por un proveedor de servicios (MSP)

El sistema opera bajo un modelo multi-tenant donde un Proveedor de Servicios Administrados (MSP) gestiona múltiples condominios, cada uno con sus propios usuarios, reglas y datos.

### 1.2 Para qué Entornos es Adecuado

| Adecuado | No Adecuado |
|----------|-------------|
| Control de acceso residencial | Infraestructura crítica |
| Comunidades cerradas | Instalaciones gubernamentales clasificadas |
| Fraccionamientos privados | Centros de datos Tier IV |
| Edificios de departamentos | Sistemas financieros transaccionales |
| Corporativos con visitantes frecuentes | Entornos que requieren certificación militar |

### 1.3 Tipo de Seguridad que Ofrece

**Sí ofrece:**
- Aislamiento de datos entre condominios (tenants)
- Trazabilidad de decisiones administrativas críticas
- Protección contra escalamiento silencioso de privilegios
- Registro inmutable de eventos de gobierno
- Separación explícita de identidad, alcance y autoridad

**No ofrece:**
- Cifrado de datos en reposo
- Autenticación multifactor
- Protección contra ataques de infraestructura (DDoS, exfiltración de red)
- Detección de intrusiones en tiempo real
- Cumplimiento automático de regulaciones específicas (PCI-DSS, HIPAA, etc.)

---

## 2. ALCANCE DE PROTECCIÓN

### 2.1 Activos Protegidos

| Activo | Nivel de Protección | Mecanismo |
|--------|---------------------|-----------|
| Datos de visitas por condominio | Aislado por tenant | Row Level Security (RLS) |
| Evidencias fotográficas | Aislado por tenant | RLS + almacenamiento segregado |
| Asignaciones de autoridad | Auditado | Triggers + eventos inmutables |
| Alcances de usuario (scopes) | Auditado | Triggers + eventos inmutables |
| Historial de decisiones críticas | Inmutable | Append-only event log |
| Credenciales de usuario | Protegido | Hash bcrypt con salt |

### 2.2 Tipos de Abuso que Mitiga

| Tipo de Abuso | Mitigación | Efectividad |
|---------------|------------|-------------|
| Usuario accede a datos de otro condominio | RLS en tablas operativas | Alta |
| Escalamiento silencioso de privilegios | Trigger de auditoría con alerta | Media-Alta |
| Borrado de autoridades sin rastro | Trigger bloquea o registra con alerta | Alta |
| Modificación de historial de eventos | Trigger bloquea UPDATE/DELETE | Alta |
| Reactivación no autorizada de permisos revocados | Trigger requiere flag explícito | Alta |
| Suplantación por credenciales débiles | bcrypt con factor de costo | Media |

### 2.3 Tipos de Ataques que NO Intenta Mitigar

| Tipo de Ataque | Razón de Exclusión |
|----------------|-------------------|
| Ataques de red (MITM, sniffing) | Responsabilidad de infraestructura |
| Fuerza bruta contra login | Requiere rate limiting en aplicación |
| Inyección SQL | Responsabilidad de aplicación (queries parametrizados) |
| XSS / CSRF | Responsabilidad de frontend |
| Compromiso de servidor de base de datos | Límite de confianza del sistema |
| Insider threat con acceso de superusuario | Aceptado como límite de confianza |
| Ingeniería social | Fuera del alcance técnico |

---

## 3. CONTROLES DE SEGURIDAD EXISTENTES

### 3.1 Gobierno de Identidad y Alcance

El sistema separa explícitamente tres conceptos:

**Identidad:** Quién es el usuario (autenticación)
- Credenciales almacenadas con hash bcrypt
- Tokens JWT con expiración temporal
- Campo descriptivo (`identity_label`) sin uso en autorización

**Alcance (Scope):** Dónde puede operar el usuario
- Tabla dedicada que vincula usuario con tenant(s)
- Nivel de acceso explícito por tenant
- Fechas de vigencia (inicio/fin)
- Estado revocable con timestamp

**Autoridad:** Qué puede hacer el usuario
- Tabla separada de autorizaciones
- Poderes explícitos (no inferidos de rol)
- Contexto de aplicación (global vs. tenant específico)
- Revocación con bloqueo de reactivación automática

### 3.2 Aislamiento Multi-Tenant

| Capa | Control | Implementación |
|------|---------|----------------|
| Base de datos | Row Level Security | Políticas RLS en tablas operativas |
| Contexto de sesión | Variable de aplicación | `SET app.tenant_id` por request |
| Queries | Filtrado automático | RLS filtra sin intervención de aplicación |

**Tablas con RLS activo:**
- `visitas`
- `evidencias`
- `casetas`
- `user_tenant_scope`

**Comportamiento:** Si la aplicación no configura el contexto de tenant correctamente, las queries retornan conjuntos vacíos o incorrectos. El sistema falla hacia restricción, no hacia permisividad.

### 3.3 Auditoría y Trazabilidad

**Eventos auditados automáticamente (via triggers):**
- Creación, modificación y eliminación de autoridades
- Creación, modificación y eliminación de alcances de usuario
- Intentos de reactivación de permisos revocados

**Contenido de cada evento:**
- Identificador único del evento
- Timestamp con zona horaria
- Tipo de evento (catálogo definido)
- Identificador del actor (quién ejecutó)
- Identificador del tenant afectado
- Hash de integridad del evento
- Metadatos específicos de la operación

**Garantías del log de eventos:**
- Append-only (solo inserción)
- UPDATE bloqueado por trigger
- DELETE bloqueado por trigger
- Orden determinístico por timestamp + ID

### 3.4 Protección contra Escalamiento Silencioso

| Escenario | Control |
|-----------|---------|
| Modificación de nivel de acceso | Trigger genera evento con `resultado = 'alerta'` |
| Eliminación de autoridad | Trigger registra DELETE con alerta |
| Reactivación de permiso revocado | Trigger bloquea sin flag `reactivation_authorized` |
| Cambio de estado de scope | Evento auditado con valores anterior/nuevo |

---

## 4. EVENT SOURCING Y AUDITORÍA

### 4.1 Cómo se Registran Decisiones Críticas

Toda decisión que afecte gobierno del sistema genera un evento inmutable:

| Categoría | Ejemplos de Eventos |
|-----------|---------------------|
| Identidad | Creación de usuario, cambio de credenciales |
| Alcance | Asignación a tenant, revocación de acceso |
| Autoridad | Otorgamiento de poder, revocación, reactivación |
| Política | Creación de límites, modificación de reglas |

Cada evento contiene:
- Qué ocurrió (tipo de evento)
- Quién lo hizo (identity_id del actor)
- Cuándo ocurrió (timestamp UTC)
- Dónde aplica (tenant_id)
- Datos específicos (metadatos JSON)
- Prueba de integridad (hash SHA-256)

### 4.2 Qué se Puede Reconstruir Históricamente

| Pregunta | Respuesta Posible |
|----------|-------------------|
| ¿Quién tenía acceso al tenant X en fecha Y? | Sí, reconstruible |
| ¿Quién otorgó autoridad Z al usuario W? | Sí, con identity_id del otorgante |
| ¿Cuándo fue revocado el acceso de usuario U? | Sí, con timestamp exacto |
| ¿Qué sesión se usó para la operación O? | Sí, session_hash registrado |
| ¿Hubo intentos de reactivación bloqueados? | Sí, eventos de bloqueo registrados |

### 4.3 Garantías del Log de Eventos

| Garantía | Mecanismo | Limitación |
|----------|-----------|------------|
| Inmutabilidad | Trigger bloquea UPDATE/DELETE | Superusuario puede desactivar triggers |
| Integridad | Hash SHA-256 por evento | No hay cadena de bloques entre eventos |
| Completitud | Triggers automáticos en tablas críticas | Eventos de aplicación dependen de la aplicación |
| Orden | Timestamp + ID lexicográfico | Resolución de milisegundos |

---

## 5. LÍMITES Y SUPUESTOS

### 5.1 Dependencias Explícitas

El sistema **requiere** que la aplicación:

| Dependencia | Consecuencia si Falla |
|-------------|----------------------|
| Configure `app.tenant_id` en cada request | RLS no filtra correctamente |
| Valide `tenant_id` contra sesión del usuario | Posible acceso cruzado entre tenants |
| Consulte autoridades antes de operaciones de gobierno | Acciones sin verificación de permisos |
| Consulte políticas antes de aplicar límites | Límites no enforced |
| Emita eventos para operaciones no cubiertas por triggers | Gaps en auditoría |
| No use `identity_label` para autorización | Decisiones basadas en campo descriptivo |

### 5.2 Riesgos Aceptados Conscientemente

| Riesgo | Justificación |
|--------|---------------|
| Superusuario de base de datos puede manipular cualquier dato | Límite de confianza necesario para operación |
| Scopes pueden no tener fecha de expiración | Caso de uso legítimo (acceso permanente) |
| Usuario puede tener scopes en múltiples tenants | Requerimiento de arquitectura multi-tenant |
| Autoridad global es omnipotente | Usuario raíz necesita poder total para bootstrap |
| JSON de políticas sin validación de schema en DB | Flexibilidad sobre rigidez |
| Sin rate limiting en capa de datos | Responsabilidad de capa de aplicación |

### 5.3 Supuestos de Confianza

| Componente | Nivel de Confianza | Implicación |
|------------|-------------------|-------------|
| Superusuario PostgreSQL | Total | Puede desactivar triggers, modificar datos |
| Aplicación | Alto | Debe configurar contexto correctamente |
| Operadores de infraestructura | Alto | Acceso a backups, logs, configuración |
| Usuarios finales | Ninguno | Todo input se valida |

---

## 6. MODELO DE RESPONSABILIDAD COMPARTIDA

### 6.1 Qué Garantiza la Base de Datos

| Control | Garantía | Condición |
|---------|----------|-----------|
| Aislamiento RLS | Datos filtrados por tenant | `app.tenant_id` configurado correctamente |
| Inmutabilidad de eventos | UPDATE/DELETE bloqueados | Conexión sin privilegios de superusuario |
| Auditoría de autoridades | Cambios registrados automáticamente | Triggers activos |
| Bloqueo de reactivación | Reactivación requiere flag explícito | Trigger activo |
| Integridad de credenciales | Passwords hasheados | Aplicación usa funciones de hash |

### 6.2 Qué Debe Garantizar la Aplicación

| Responsabilidad | Riesgo si no se Cumple |
|-----------------|------------------------|
| Autenticación correcta de usuarios | Suplantación de identidad |
| Configuración de `app.tenant_id` | Bypass de aislamiento |
| Validación de tenant contra sesión | Acceso cruzado entre tenants |
| Consulta de autoridades antes de operar | Acciones sin permiso |
| Emisión de eventos para operaciones no auditadas | Gaps en trazabilidad |
| Rate limiting | Ataques de fuerza bruta |
| Sanitización de inputs | Inyección SQL |
| Gestión segura de JWT | Robo de sesión |

### 6.3 Qué es Responsabilidad Operativa del Cliente

| Responsabilidad | Impacto |
|-----------------|---------|
| Control de acceso a base de datos | Exposición de datos si se compromete |
| Rotación de credenciales de superusuario | Acceso no autorizado prolongado |
| Backups y recuperación | Pérdida de datos |
| Monitoreo de alertas de auditoría | Incidentes no detectados |
| Revisión periódica de scopes y autoridades | Privilegios acumulados |
| Capacitación de administradores | Errores operativos |
| Políticas de retención de eventos | Compliance |

---

## 7. CASOS DE USO ADECUADOS / NO ADECUADOS

### 7.1 Dónde MSP_AXS es una Buena Elección

| Escenario | Por qué es Adecuado |
|-----------|---------------------|
| Condominio residencial con 50-500 unidades | Escala apropiada, modelo multi-tenant |
| Empresa administradora de múltiples comunidades | Un MSP, múltiples tenants aislados |
| Entorno que requiere auditoría de accesos | Event sourcing inmutable |
| Operación donde transparencia es importante | Trazabilidad de decisiones |
| Clientes que necesitan reportes de visitas | Datos estructurados y consultables |
| Organizaciones con rotación de personal | Revocación de accesos auditable |

### 7.2 Dónde NO es la Herramienta Correcta

| Escenario | Por qué NO es Adecuado |
|-----------|------------------------|
| Instalaciones con requisitos de clasificación gubernamental | Sin certificaciones formales |
| Entornos que requieren MFA obligatorio | No implementado en capa de datos |
| Sistemas que procesan datos de tarjetas de pago | No cumple PCI-DSS |
| Infraestructura crítica (energía, agua, telecomunicaciones) | Modelo de amenazas no alineado |
| Organizaciones que requieren cifrado en reposo certificado | No implementado |
| Entornos con requisitos de disponibilidad 99.99%+ | Sin arquitectura de alta disponibilidad documentada |
| Sistemas que requieren segregación de duties formal | Sin workflow de aprobación dual |

---

## 8. CONCLUSIÓN

### 8.1 Postura de Seguridad Final

MSP_AXS implementa un modelo de seguridad orientado a:

- **Trazabilidad:** Decisiones críticas registradas de forma inmutable
- **Aislamiento:** Datos de tenants separados en capa de base de datos
- **Transparencia:** Eventos auditables que permiten reconstrucción histórica
- **Prevención de escalamiento silencioso:** Cambios de privilegios generan alertas

El sistema **no** intenta ser una solución de seguridad completa. Depende explícitamente de:

- Una aplicación que configure correctamente el contexto de tenant
- Operadores que controlen el acceso a la base de datos
- Infraestructura que proteja la red y el servidor

### 8.2 Mensaje al Evaluador

Si está evaluando MSP_AXS para su organización, considere:

**Sí adopte MSP_AXS si:**
- Su caso de uso es control de acceso residencial o corporativo de visitantes
- Necesita trazabilidad de decisiones administrativas
- Administra múltiples comunidades desde un punto central
- Valora la transparencia sobre la opacidad
- Tiene capacidad de operar una aplicación web correctamente

**No adopte MSP_AXS si:**
- Requiere certificaciones de seguridad formales (ISO 27001, SOC 2, etc.)
- Su modelo de amenazas incluye atacantes sofisticados con recursos estatales
- Necesita MFA, cifrado en reposo, o DLP integrados
- No tiene personal técnico para operar la aplicación correctamente
- Espera que el sistema compense errores de configuración

**Lo que puede esperar:**
- Un sistema que registra quién hizo qué y cuándo
- Datos de un condominio no accesibles desde otro
- Alertas cuando alguien intenta escalar privilegios
- Capacidad de responder "¿quién tenía acceso el día X?"

**Lo que NO debe esperar:**
- Que el sistema detecte o bloquee ataques de red
- Que compense una aplicación mal implementada
- Que proteja contra un administrador de base de datos malicioso
- Que cumpla automáticamente con regulaciones específicas

---

## ANEXO: MATRIZ DE CONTROLES PARA AUDITORÍA RÁPIDA

| Control | Existe | Dónde | Limitación |
|---------|--------|-------|------------|
| Aislamiento multi-tenant | ✓ | RLS en PostgreSQL | Depende de `app.tenant_id` |
| Hash de passwords | ✓ | bcrypt en DB | Sin política de complejidad |
| Auditoría de autoridades | ✓ | Triggers automáticos | Solo tablas de gobierno |
| Inmutabilidad de eventos | ✓ | Trigger bloquea UPDATE/DELETE | Superuser puede bypass |
| Bloqueo de reactivación | ✓ | Trigger con flag | Requiere flag explícito |
| Rate limiting | ✗ | — | Responsabilidad de aplicación |
| MFA | ✗ | — | No implementado |
| Cifrado en reposo | ✗ | — | Depende de infraestructura |
| Segregación de duties | ✗ | — | Sin workflow dual |
| Detección de intrusiones | ✗ | — | Fuera de alcance |

---

**FIN DEL DOCUMENTO — SECURITY POSTURE v1.0.0**
