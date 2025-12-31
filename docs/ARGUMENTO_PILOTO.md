# ARGUMENTO TÉCNICO-COMERCIAL PARA PILOTO
## MSP_AXS — Por qué esto no es otro sistema de QR

---

## EL PROBLEMA QUE NADIE RESUELVE

Hoy, cuando un condominio compra un "sistema de acceso con QR", compra:
- Una app que genera códigos
- Una base de datos que guarda visitas
- Un panel que muestra reportes

**Pero nadie te da las respuestas a:**

1. **¿Quién permitió esto?**  
   Si un guardia genera 50 QR en una hora, ¿fue él o alguien usó su sesión?

2. **¿Hasta dónde puede llegar?**  
   Si un administrador crea 10 torres nuevas, ¿tenía permiso para hacerlo?

3. **¿Qué pasó exactamente?**  
   Si hay una demanda por un incidente, ¿tienes evidencia que resista auditoría forense?

4. **¿Quién controla el poder?**  
   Si necesitas desactivar a un usuario o limitar acciones, ¿lo haces editando la base de datos manualmente?

---

## LO QUE CAMBIA CON MSP_AXS

### 1. **IDENTIDAD CERTIFICADA** (no solo login)

**Sin AUP:**  
"Usuario123 generó un QR" → ¿Fue él o alguien con su contraseña?

**Con MSP_AXS:**  
Cada sesión tiene un token criptográfico que expira en 60 minutos.  
Si alguien roba la contraseña, tiene 60 minutos antes de que el sistema lo expulse automáticamente.  
**Evidencia:** Token JWT con timestamp, IP, y hash SHA-256 del evento de login.

**Cliente entiende:** Si hay problema, sabemos QUIÉN fue con certeza matemática.

---

### 2. **ALCANCE EXPLÍCITO** (no solo permisos)

**Sin AUP:**  
Un administrador de Torre A puede ver datos de Torre B porque "tiene rol de admin".

**Con MSP_AXS:**  
Cada usuario está asignado a UN condominio (scope).  
Físicamente no puede ver datos de otro scope.  
No es permiso (que se puede hackear), es aislamiento arquitectónico.

**Cliente entiende:** Torre A jamás puede ver Torre B. Punto.

---

### 3. **TRAZABILIDAD INMUTABLE** (no solo logs)

**Sin AUP:**  
"Logs de actividad" que se pueden borrar o editar.

**Con MSP_AXS:**  
Cada acción crítica genera un evento con:
- Hash SHA-256 del payload completo
- Timestamp ISO-8601
- Usuario + scope + acción + metadata

Los eventos NO se pueden borrar ni editar.  
Si intentas modificar uno, el hash cambia y se detecta la manipulación.

**Cliente entiende:** Si hay una auditoría legal, tienes evidencia forense certificada.

---

### 4. **GOBIERNO ACTIVO** (no solo roles)

**Sin AUP:**  
"Roles y permisos" que el administrador configura manualmente.  
Si necesitas cambiar límites, editas la base de datos o llamas al proveedor.

**Con MSP_AXS:**  
Políticas de gobierno que se evalúan EN TIEMPO REAL:
- ¿Cuántos QR puede generar al día? → Política "qr_vigencia_dias"
- ¿Cuántos tenants puede crear? → Política "max_tenants"
- ¿Cuántos usuarios puede tener el condominio? → Política "max_usuarios_por_tenant"

**Si la política dice "5 tenants máximo", el sistema bloquea el sexto.**  
No es advertencia, es bloqueo técnico.

**Cliente entiende:** El sistema te protege de errores operativos y abusos.

---

## RIESGOS ELIMINADOS

| Riesgo tradicional | Cómo MSP_AXS lo elimina |
|--------------------|-------------------------|
| **Robo de sesión** | Tokens que expiran en 60 minutos + hash SHA-256 |
| **Acceso cruzado entre condominios** | Aislamiento de scope (físico, no lógico) |
| **Evidencia manipulable** | Eventos inmutables con hash SHA-256 |
| **Escalada de privilegios** | Gobierno evalúa políticas ANTES de ejecutar |
| **"No sé quién hizo esto"** | Cada evento tiene usuario + scope + timestamp + hash |
| **Límites que se ignoran** | Políticas bloquean técnicamente (no son avisos) |

---

## EVIDENCIA QUE OBTIENES

### Ante una auditoría legal:
- **Cadena de custodia:** Cada QR generado tiene evento con hash SHA-256
- **No repudio:** Usuario no puede negar acción si su token firmó el evento
- **Integridad temporal:** Timestamps ISO-8601 certifican orden cronológico
- **Trazabilidad completa:** De login → acción → resultado

### Ante un incidente operativo:
- **¿Quién generó 100 QR en una hora?** → Query a tabla `aup_events`
- **¿Cuándo se cambió el plan comercial?** → Evento tipo "politica_asignada"
- **¿Qué usuario accedió a qué scope?** → Evento tipo "sesion_iniciada"

### Ante cambio de proveedor:
- **Tienes tus datos:** Eventos exportables en JSON/CSV
- **Tienes evidencia:** Hashes que puedes re-verificar fuera del sistema
- **No hay lock-in:** Arquitectura abierta (no black box)

---

## POR QUÉ EL PILOTO ES SEGURO PARA EL CLIENTE

### 1. **INFRAESTRUCTURA PROPIA**
- Base de datos PostgreSQL en Neon (cloud serverless)
- Backend Python/FastAPI (open source, auditable)
- No dependencia de servicios propietarios cerrados

### 2. **REVERSIBILIDAD**
- Exportas tus eventos y datos en cualquier momento
- Hashes te permiten verificar integridad fuera del sistema
- Arquitectura FastAPI es estándar de industria (fácil migrar)

### 3. **CONTROL DE RIESGO**
- Plan FREE: Límites controlados (5 tenants, 100 usuarios, QR 7 días)
- Sin tarjeta de crédito para empezar
- Upgrade/downgrade sin penalización (políticas se aplican instantáneamente)

### 4. **EVIDENCIA DESDE DÍA 1**
- Cada acción del piloto genera evento auditable
- Si el piloto falla, tienes trazabilidad completa del por qué
- Si el piloto funciona, tienes evidencia para justificar expansión

---

## DISCURSO DE 5 MINUTOS (PITCH PARA CONDOMINIO)

### Minuto 1 — El Problema
"Hoy, su condominio tiene guardias que generan QR, administradores que crean usuarios, y una base de datos que guarda todo. Pero si hay un incidente y les preguntan '¿quién autorizó esta entrada?', ustedes no tienen evidencia certificada. Tienen logs que se pueden borrar."

### Minuto 2 — Qué Cambia
"MSP_AXS no es un sistema de QR. Es una infraestructura gobernada. Cada acción deja un evento inmutable con hash SHA-256. Si alguien genera 100 QR en una hora, ustedes lo ven EN TIEMPO REAL. Si alguien intenta acceder a datos de otra torre, el sistema lo bloquea arquitectónicamente."

### Minuto 3 — Control Real
"Ustedes deciden límites: ¿Cuántos QR al día? ¿Cuántos usuarios por condominio? ¿Cuántos días de vigencia? Y el sistema los aplica técnicamente. No es un aviso, es un bloqueo. Si la política dice '5 tenants', el sexto no se crea. Punto."

### Minuto 4 — Evidencia Forense
"Si hay una demanda, ustedes tienen cadena de custodia certificada. Cada evento tiene timestamp ISO-8601, hash SHA-256, usuario, y acción. Un juez puede verificar que esos eventos no fueron manipulados. Eso no existe en sistemas tradicionales."

### Minuto 5 — Por Qué Piloto Ahora
"El piloto es gratis, sin tarjeta de crédito. Empiezan con límites controlados (100 usuarios, 5 torres, QR de 7 días). Si funciona, escalan. Si no, tienen evidencia completa del por qué falló. Y lo más importante: desde el primer día, tienen control y evidencia. Eso no tiene precio cuando hay un incidente."

---

## 3 DIFERENCIALES IMPOSIBLES DE COPIAR RÁPIDO

### 1. **GOBIERNO ANTES DE OPERACIÓN**
**Qué es:** Cada acción crítica consulta políticas ANTES de ejecutarse.

**Por qué es difícil copiar:**  
Requiere separar 2 planos (operación vs poder) desde la arquitectura.  
La competencia tiene roles mezclados con lógica de negocio.  
Refactorizar eso toma meses y rompe todo el código existente.

**Evidencia técnica:** `backend/core/gov/facade.py` → `puede_ejecutar_accion()`  
Consulta política → Si deniega, bloquea → Si permite, ejecuta + registra evento.

**Cliente entiende:** "El sistema me protege de errores y abusos técnicamente, no con avisos."

---

### 2. **EVENTOS INMUTABLES CON HASH SHA-256**
**Qué es:** Cada acción crítica genera evento con hash del payload completo.

**Por qué es difícil copiar:**  
Requiere arquitectura event-sourcing desde día 1.  
La competencia tiene logs que se pueden borrar.  
Migrar a inmutabilidad significa re-diseñar el modelo de datos.

**Evidencia técnica:** `backend/core/event/registry.py` → `registrar_evento_aup()`  
Calcula SHA-256 de `{tipo_evento, alcance_id, usuario_id, metadata}`.  
Guarda en tabla `aup_events` con índices para queries forenses.

**Cliente entiende:** "Si hay auditoría legal, tengo evidencia que resiste manipulación."

---

### 3. **SCOPE COMO ISOLACIÓN ARQUITECTÓNICA**
**Qué es:** Cada tenant (condominio) es un scope físicamente aislado.

**Por qué es difícil copiar:**  
Requiere multi-tenancy desde la arquitectura, no solo flag en tabla.  
La competencia tiene `tenant_id` en WHERE clauses (fácil de omitir por error).  
MSP_AXS valida scope en DEPENDENCIAS (antes de entrar al router).

**Evidencia técnica:** `backend/core/scope/dependencies.py` → `validar_contexto_con_scope()`  
Si usuario.scope_id != recurso.scope_id → 403 Forbidden.  
No hay forma de saltarse esta validación (está en la capa de infraestructura).

**Cliente entiende:** "Torre A jamás puede ver datos de Torre B. Punto."

---

## VALOR INMEDIATO DEL PILOTO

### Para el Administrador del Condominio
✅ **Control visual:** Dashboard con eventos en tiempo real  
✅ **Límites claros:** Sabe exactamente cuántos QR/usuarios/torres puede crear  
✅ **Auditoría instantánea:** Query "¿quién generó QR hoy?" en 2 clicks  
✅ **Sin riesgo:** Piloto gratis, exportable, reversible

### Para el Guardia de Seguridad
✅ **QR confiable:** Cada código tiene validación criptográfica  
✅ **Trazabilidad:** Si hay problema, no es culpa del guardia (hay evidencia del flujo completo)  
✅ **Sin confusión:** Sistema bloquea acciones no permitidas (no depende de memoria del guardia)

### Para el Residente
✅ **Pre-registro sin fricción:** Envía datos de visita antes de que llegue  
✅ **QR temporal:** No queda registro permanente innecesario (vigencia controlada)  
✅ **Privacidad:** Datos aislados por condominio (Torre A no ve Torre B)

### Para el Abogado (en caso de incidente)
✅ **Cadena de custodia:** Eventos con hash SHA-256 verificables  
✅ **No repudio:** Usuario no puede negar acción firmada con su token  
✅ **Exportabilidad:** CSV/JSON de eventos para peritaje externo

---

## CALL TO ACTION

**"El piloto empieza en 48 horas."**

1. **Hoy:** Definimos 1 torre para piloto  
2. **Mañana:** Creamos 5 usuarios (admin + guardias)  
3. **Día 3:** Primer QR generado con evidencia completa  
4. **Semana 1:** Primera auditoría de eventos (query forense real)  
5. **Mes 1:** Decisión de expansión o cierre (con evidencia completa del por qué)

**Sin tarjeta de crédito. Sin lock-in. Con evidencia desde minuto 1.**

---

## RESUMEN EJECUTIVO (30 SEGUNDOS)

MSP_AXS no es un sistema de QR.  
Es infraestructura gobernada con evidencia forense certificada.  

**3 ventajas:**
1. Gobierno técnico (bloquea, no avisa)  
2. Eventos inmutables (evidencia legal)  
3. Aislamiento arquitectónico (privacidad física)

**Piloto gratis, evidencia desde día 1, reversible en cualquier momento.**

**¿Cuándo empezamos?**

---

## ANEXO: RESPUESTAS A OBJECIONES COMUNES

### "Ya tenemos un sistema de QR que funciona"
**Respuesta:** ¿Tienen evidencia forense de cada QR generado? Si mañana hay un incidente y les preguntan "¿quién autorizó esta entrada a las 3 AM?", ¿tienen hash SHA-256 del evento con timestamp certificado? Si no, no tienen sistema. Tienen base de datos editable.

### "Esto suena muy técnico para nosotros"
**Respuesta:** Ustedes no necesitan entender SHA-256. Necesitan poder decir ante un juez: "Aquí está la evidencia certificada de lo que pasó". Eso es lo que MSP_AXS les da. El resto es infraestructura (como no necesitan entender cómo funciona el aire acondicionado para usarlo).

### "¿Qué pasa si su empresa desaparece?"
**Respuesta:** Exportan sus eventos y datos en JSON/CSV. Los hashes SHA-256 son verificables fuera del sistema. La arquitectura es FastAPI + PostgreSQL (estándar open source). Cualquier programador puede continuar el código. No hay lock-in.

### "No tenemos presupuesto ahora"
**Respuesta:** El piloto es gratis (Plan FREE: 5 tenants, 100 usuarios, QR 7 días). Si el piloto funciona, justifican el presupuesto con evidencia real. Si no funciona, no pagaron nada. Es risk-free.

### "¿Cuánto tiempo toma implementar?"
**Respuesta:** 48 horas para primer usuario + primer QR. 1 semana para 5 usuarios activos. 1 mes para decisión de expansión con data real.

---

**Construido con Architecture from Unified Principles (AUP)**  
**Versión: 3.0.0-aup-gov**  
**Fecha: Diciembre 2024**
