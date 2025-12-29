# ═══════════════════════════════════════════════════════════════════════════
# VERTICALIZACIÓN AUP — RESIDENCIAL / CONTROL DE ACCESOS
# ═══════════════════════════════════════════════════════════════════════════

## DECLARACIÓN DE VERTICAL

**Dominio seleccionado:** RESIDENCIAL / CONTROL DE ACCESOS

**Razón de selección:**
- Claridad estructural máxima (actores, recursos, riesgos definidos)
- Alto impacto en seguridad física (no solo datos)
- Poder distribuido (MSP, condominio, residente, vigilante)
- Trazabilidad crítica (quién entró cuándo dónde por qué)
- Monetización evidente (escalado por tenant = condominios)

**Contexto operativo:**
Sistema multi-tenant donde un MSP (proveedor de servicios) opera plataforma para múltiples condominios. Cada condominio tiene residentes, vigilantes, administradores. El sistema controla acceso físico mediante QR, registro de visitas, y políticas de entrada.

---

## 📊 TABLA DE MAPEO: AUP → VERTICAL RESIDENCIAL

### **AUP_IDENTITY → ACTOR DEL SISTEMA**

```
Manifestación en Vertical:
  - Residente (dueño/inquilino de unidad)
  - Vigilante (operador de acceso)
  - Admin de condominio (gestor local)
  - MSP Admin (proveedor de plataforma)
  - Visita (actor temporal, pre-registrado)

Entidad Real:
  Usuario físico con credenciales digitales (email/password + biometría opcional)

Riesgo Controlado:
  Suplantación de identidad (quién dice ser vs quién es)
  Acceso no autorizado (actor sin derecho de entrada)

Valor Generado:
  Identidad verificable en todo momento
  Revocación instantánea (despido de vigilante, mudanza de residente)
  Auditoría de responsabilidad (quién aprobó acceso)
```

### **AUP_CREDENTIAL → PRUEBA DE AUTENTICIDAD**

```
Manifestación en Vertical:
  - Password + bcrypt hash
  - QR code firmado (visita pre-registrada)
  - Biometría (huella, rostro) [futuro]
  - Badge RFID vinculado a identidad [futuro]

Entidad Real:
  Token criptográfico que prueba "yo soy quien digo ser"

Riesgo Controlado:
  Clonación de credencial (QR screenshotted y compartido)
  Uso posterior a revocación (QR expirado pero guardado)
  Fuerza bruta (password débil)

Valor Generado:
  Credencial con vigencia explícita (QR válido 7 días)
  Credencial revocable (suspender QR si visita sospechosa)
  Credencial auditable (quién generó QR para quién)
```

### **AUP_SESSION → CONTEXTO TEMPORAL DE OPERACIÓN**

```
Manifestación en Vertical:
  - Sesión de vigilante en turno (8 horas)
  - Sesión de residente en app móvil (30 minutos inactividad)
  - Sesión de visita en predio (desde entrada hasta salida)
  - Sesión de admin gestionando condominio (1 hora)

Entidad Real:
  JWT con expiración que habilita operaciones mientras está activo

Riesgo Controlado:
  Operación fuera de turno (vigilante despedido sigue teniendo acceso)
  Sesión secuestrada (JWT robado en tránsito)
  Acceso prolongado sin re-autenticación

Valor Generado:
  Contexto temporal explícito (operación válida solo en tiempo X)
  Revocación por expiración automática (no requiere intervención)
  Auditoría de tiempo real (quién operó cuándo)
```

### **AUP_SCOPE → ALCANCE ESPACIAL Y OPERATIVO**

```
Manifestación en Vertical:
  - Residente: LECTURA en su condominio, ESCRITURA en su unidad
  - Vigilante: LECTURA+ESCRITURA en registro de accesos de su condominio
  - Admin condominio: LECTURA+ESCRITURA en TODO su condominio
  - MSP Admin: LECTURA en TODOS los condominios, ESCRITURA en configuración global
  - Visita: LECTURA de su QR (no puede ver otros registros)

Entidad Real:
  Alcance explícito que responde "¿qué puedes hacer dónde?"

Riesgo Controlado:
  Escalada de privilegios (vigilante de Condo A accede a Condo B)
  Acceso cruzado (residente lee datos de otro residente)
  Operación sin límites (admin local crea usuarios en otro condominio)

Valor Generado:
  Aislamiento multi-tenant nativo (data leak imposible por diseño)
  Alcance dinámico (residente se muda → cambio de scope instantáneo)
  Auditoría de alcance (quién operó en qué condominio)
```

### **AUP_TENANT → CONTENEDOR DE OPERACIÓN**

```
Manifestación en Vertical:
  - Condominio (edificio, conjunto residencial, fraccionamiento)
  - Cada tenant tiene:
    - Unidades (departamentos, casas)
    - Residentes (identidades asignadas)
    - Vigilantes (operadores de acceso)
    - Políticas locales (horarios, límite de visitas)
    - Evidencias (fotos de acceso, incidentes)

Entidad Real:
  Contenedor físico-digital que agrupa datos y operaciones de un cliente

Riesgo Controlado:
  Mezcla de datos entre condominios (visita de Condo A aparece en Condo B)
  Operación sin contenedor (registro sin saber a qué condominio pertenece)
  Fuga de datos sensibles (admin de Condo A ve fotos de Condo B)

Valor Generado:
  Aislamiento total (cada condominio es universo independiente)
  Escalado horizontal (agregar condominio = nuevo tenant, no código)
  Monetización por tenant (cobro por condominio activo)
```

### **AUP_EVENT → DECLARACIÓN DE HECHO INMUTABLE**

```
Manifestación en Vertical:
  - Registro de acceso (quién entró, cuándo, por dónde, aprobado por quién)
  - Generación de QR (residente genera QR para visita, vigencia 3 días)
  - Suspensión de usuario (admin suspende vigilante, motivo registrado)
  - Modificación de política (cambio de horario de acceso, quién lo aprobó)
  - Incidente de seguridad (acceso denegado, intento con QR expirado)

Entidad Real:
  Bitácora inmutable de TODO lo que ocurre en el sistema

Riesgo Controlado:
  Repudio (vigilante niega haber aprobado acceso sospechoso)
  Alteración de historial (borrar registro de acceso no autorizado)
  Incidente sin responsable (acceso irregular sin auditoría)

Valor Generado:
  Trazabilidad total (reconstrucción forense de cualquier evento)
  Compliance nativo (auditoría lista para autoridades)
  Responsabilidad explícita (cada acción tiene actor + timestamp)
  Detección de patrones (alerta si QR usado fuera de vigencia)
```

### **AUP_GOV → GOBIERNO Y META-PODER**

```
Manifestación en Vertical:
  - MSP Admin como GLOBAL AUTHORITY (crea condominios, asigna first-tier)
  - Admin de condominio como FIRST-TIER AUTHORITY (crea vigilantes, residentes)
  - Políticas de límites:
    - Condominio gratuito: máx 1 vigilante, 10 residentes, QR 3 días vigencia
    - Condominio premium: máx 5 vigilantes, 100 residentes, QR 30 días vigencia
    - MSP: máximo 20 condominios por first-tier (evita revendedores descontrolados)
  - Delegaciones temporales:
    - Admin delega a sub-admin capacidad de crear residentes por 30 días
    - Vigilante recibe delegación para aprobar visitas sin QR (emergencia)

Entidad Real:
  Plano de control que decide quién puede crear, limitar, suspender

Riesgo Controlado:
  Escalado descontrolado (cualquiera crea condominios sin límite)
  Operación sin política (vigilante genera QRs de 365 días)
  Poder irrevocable (admin despedido sigue creando usuarios)

Valor Generado:
  Monetización estructural (planes Free/Pro/Enterprise via políticas)
  Gobierno dinámico (cambiar límites sin redeploy)
  Delegación controlada (poder temporal + revocable)
  Auditoría de poder (quién creó qué, con qué authority)
```

---

## 🔄 FLUJO OPERATIVO REAL: VISITA CON QR

### **Escenario: Residente registra visita, vigilante valida acceso**

#### **PASO 1: Residente Inicia Sesión**

```
AUP_IDENTITY: Juan Pérez (residente, unidad 302, Condo "Las Palmas")
AUP_CREDENTIAL: Email + password (bcrypt validado)
AUP_SESSION: JWT generado, válido 30 minutos
AUP_SCOPE: Habilitado en tenant "condo_las_palmas", alcance LECTURA+ESCRITURA en unidad 302
AUP_EVENT: Registrado "login exitoso, ip: 192.168.1.50, timestamp: 2025-12-29 10:15:00"
```

**Estado:** Residente autenticado, contexto activo.

#### **PASO 2: Residente Genera QR para Visita**

```
OPERACIÓN: Juan genera QR para "María López" (amiga), vigencia 3 días

VALIDACIÓN DE GOBIERNO:
  AUP_GOV evalúa política:
    - ¿Juan tiene authority? NO (es residente, no admin)
    - ¿Juan tiene permiso delegado? NO
    - ¿Juan está en su scope? SÍ (operación en su unidad)
    - ¿Existe política que limite vigencia QR? SÍ (máx 7 días para plan Free)
    - ¿3 días < 7 días? SÍ → PERMITIDO

EJECUCIÓN:
  1. Sistema genera QR: qr_abc123xyz, vigencia: 2025-12-29 a 2026-01-01
  2. QR vinculado a: visita "María López", unidad 302, residente "Juan Pérez"
  3. AUP_EVENT registra:
     - actor: Juan Pérez (usuario_id: usr_123)
     - acción: generar_qr
     - entidad: preregistro_id: pre_456
     - metadata: {"vigencia_dias": 3, "visita": "María López"}
     - resultado: EXITO
     - timestamp: 2025-12-29 10:17:00

AUP_SCOPE: Operación ejecutada en tenant "condo_las_palmas", scope de Juan
AUP_TENANT: QR pertenece a tenant "condo_las_palmas"
```

**Estado:** QR generado, vigente, auditable.

#### **PASO 3: Visita Llega al Condominio**

```
CONTEXTO: 2025-12-30 15:00 (dentro de vigencia)
ACTOR: María López presenta QR en caseta de vigilancia
```

#### **PASO 4: Vigilante Valida QR**

```
AUP_IDENTITY: Pedro Ramírez (vigilante, turno 14:00-22:00)
AUP_SESSION: JWT activo (inició sesión al comenzar turno)
AUP_SCOPE: Habilitado en tenant "condo_las_palmas", alcance LECTURA+ESCRITURA en registro_accesos

OPERACIÓN: Pedro escanea QR con tablet del sistema

VALIDACIÓN:
  1. Sistema valida QR:
     - ¿QR existe? SÍ (qr_abc123xyz en BD)
     - ¿QR vigente? SÍ (2025-12-30 dentro de rango 12-29 a 01-01)
     - ¿QR pertenece a este tenant? SÍ (condo_las_palmas)
     - ¿QR ya usado? NO (usado_en: null)
     - ¿QR revocado? NO (estado: ACTIVO)
  
  2. Sistema aprueba acceso:
     - Marca QR como usado (usado_en: 2025-12-30 15:00)
     - Crea registro de visita:
       - visita_id: vis_789
       - nombre: María López
       - unidad_destino: 302
       - vigilante_aprobador: Pedro Ramírez
       - hora_entrada: 2025-12-30 15:00
       - hora_salida: null (aún dentro)
  
  3. AUP_EVENT registra:
     - actor: Pedro Ramírez (usuario_id: usr_456)
     - acción: aprobar_acceso
     - entidad: visita_id: vis_789
     - metadata: {
         "qr_id": "qr_abc123xyz",
         "residente": "Juan Pérez",
         "unidad": "302",
         "metodo": "qr"
       }
     - resultado: EXITO
     - timestamp: 2025-12-30 15:00:23

AUP_TENANT: Visita registrada en tenant "condo_las_palmas"
AUP_SCOPE: Operación ejecutada en scope de vigilante (registro_accesos)
```

**Estado:** Visita aprobada, dentro del condominio, auditable.

#### **PASO 5: Visita Sale del Condominio**

```
OPERACIÓN: Pedro registra salida de María López

EJECUCIÓN:
  1. Sistema actualiza visita:
     - hora_salida: 2025-12-30 17:30
  
  2. AUP_EVENT registra:
     - actor: Pedro Ramírez
     - acción: registrar_salida
     - entidad: visita_id: vis_789
     - metadata: {"duracion_minutos": 150}
     - resultado: EXITO
     - timestamp: 2025-12-30 17:30:45

AUP_SCOPE: Operación en scope de vigilante
AUP_TENANT: Visita cerrada en tenant "condo_las_palmas"
```

**Estado:** Flujo completo, totalmente auditable.

---

## 🚨 INCIDENTE CRÍTICO: QR CLONADO Y COMPARTIDO

### **Escenario de Ataque**

```
CONTEXTO:
  Juan Pérez genera QR para su amiga María López (vigencia 3 días).
  María comparte screenshot del QR con su novio Carlos (NO autorizado).
  Carlos intenta usar el mismo QR al día siguiente.

AMENAZA:
  - Acceso no autorizado (Carlos nunca fue pre-registrado)
  - QR usado dos veces (María ayer, Carlos hoy)
  - Responsabilidad difusa (¿quién dejó entrar a Carlos?)
```

### **CONTENCIÓN AUP (Paso a Paso)**

#### **PASO 1: Detección en Tiempo Real**

```
Carlos llega a caseta, presenta QR (screenshot).
Vigilante escanea QR.

VALIDACIÓN AUP:
  1. ¿QR existe? SÍ (qr_abc123xyz)
  2. ¿QR vigente? SÍ (aún dentro de 3 días)
  3. ¿QR ya usado? SÍ ← ALERTA
     - usado_en: 2025-12-30 15:00
     - visitante: María López
     - hora_salida: 2025-12-30 17:30
  
  4. Sistema DENIEGA acceso:
     - Razón: "QR ya consumido (uso único)"
     - Sistema muestra a vigilante:
       "⚠️ QR usado anteriormente por María López el 30/12 a las 15:00.
        Persona actual NO coincide con registro.
        ACCESO DENEGADO."

AUP_EVENT registra:
  - actor: Carlos (identidad desconocida)
  - acción: intento_acceso_denegado
  - entidad: qr_id: qr_abc123xyz
  - metadata: {
      "motivo": "qr_ya_usado",
      "uso_previo": {
        "visitante": "María López",
        "fecha": "2025-12-30 15:00"
      },
      "vigilante": "Pedro Ramírez"
    }
  - resultado: DENEGADO
  - timestamp: 2025-12-31 10:15:00
  - severidad: ALTA (intento con QR compartido)
```

**Contención:** Acceso bloqueado automáticamente.

#### **PASO 2: Notificación y Escalamiento**

```
Sistema genera alerta:
  → Notificación a Juan Pérez (residente que generó QR):
    "⚠️ Tu QR para María López fue usado por persona diferente.
     Acceso denegado. Revisa tu seguridad."
  
  → Notificación a Admin de condominio:
    "⚠️ Intento de acceso con QR compartido.
     Unidad 302 (Juan Pérez).
     Revisar incidente."

AUP_EVENT: Notificaciones registradas en auditoría
```

**Escalamiento:** Admin puede revocar QR si confirma abuso.

#### **PASO 3: Revocación de QR (Gobierno)**

```
Admin de condominio decide revocar QR:

AUP_GOV ejecuta:
  1. Admin tiene FIRST-TIER AUTHORITY en "condo_las_palmas"
  2. Admin marca QR como REVOCADO
  3. Motivo: "QR compartido indebidamente, intento de acceso no autorizado"
  
  4. AUP_EVENT registra:
     - actor: Admin (usuario_id: usr_admin)
     - acción: revocar_qr
     - entidad: qr_id: qr_abc123xyz
     - metadata: {
         "motivo": "QR compartido indebidamente",
         "residente_responsable": "Juan Pérez (usr_123)",
         "intentos_denegados": 1
       }
     - resultado: EXITO
     - timestamp: 2025-12-31 10:30:00

AUP_TENANT: QR revocado en tenant "condo_las_palmas"
AUP_SCOPE: Operación ejecutada con authority de admin
```

**Estado:** QR permanentemente revocado, no puede usarse nunca más.

#### **PASO 4: Análisis Forense Post-Incidente**

```
Admin consulta auditoría:

QUERY: "Mostrar historial completo de qr_abc123xyz"

AUP_EVENT retorna:
  1. 2025-12-29 10:17:00 - Juan Pérez generó QR (vigencia 3 días)
  2. 2025-12-30 15:00:23 - María López accedió (aprobado por vigilante Pedro)
  3. 2025-12-30 17:30:45 - María López salió (duración 150 min)
  4. 2025-12-31 10:15:00 - Carlos intentó acceso (DENEGADO, QR ya usado)
  5. 2025-12-31 10:30:00 - Admin revocó QR (motivo: compartido indebidamente)

CONCLUSIONES:
  - QR generado correctamente por residente
  - Primera visita (María) legítima
  - Segundo intento (Carlos) bloqueado por sistema
  - No hubo brecha de seguridad (acceso denegado)
  - Responsable: Juan Pérez (compartió QR indebidamente)
```

**Resultado:** Incidente contenido, cadena de responsabilidad clara, compliance garantizado.

---

## 💎 POR QUÉ ESTA VERTICAL ES IDEAL PARA AUP

### **1. Poder Distribuido (Múltiples Authorities)**

```
SIN AUP:
  Sistema monolítico con roles hardcoded.
  "Admin puede todo, vigilante puede poco."
  No hay delegación temporal.
  No hay límites dinámicos.

CON AUP:
  AUP_GOV define QUIÉN puede QUÉ:
    - MSP Admin: GLOBAL AUTHORITY (crea condominios)
    - Admin condominio: FIRST-TIER AUTHORITY (crea residentes/vigilantes)
    - Vigilante: DELEGACIÓN temporal (aprobar sin QR en emergencia)
  
  Poder es revocable, auditable, acotado.
```

**Valor:** Gobierno descentralizado sin perder control.

### **2. Trazabilidad Crítica (Responsabilidad Legal)**

```
ESCENARIO LEGAL:
  Robo en unidad 302.
  Policía pregunta: "¿Quién entró a esa unidad el día del robo?"

SIN AUP:
  Logs dispersos, incompletos, alterables.
  Vigilante puede negar haber aprobado acceso.

CON AUP:
  AUP_EVENT retorna:
    - 2025-12-30 14:45 - Visita "X" aprobada por vigilante Pedro
    - 2025-12-30 14:50 - Visita entró (foto de evidencia tomada)
    - 2025-12-30 16:30 - Visita salió
  
  Cadena de responsabilidad inmutable:
    - Residente Juan generó QR
    - Vigilante Pedro aprobó acceso
    - Sistema registró entrada/salida
```

**Valor:** Auditoría lista para autoridades (compliance nativo).

### **3. Aislamiento Multi-Tenant (Data Leaks Imposibles)**

```
RIESGO:
  Vigilante de Condominio A ve visitas de Condominio B.
  Admin de Condominio A crea usuarios en Condominio B.

SIN AUP:
  Validación manual en cada endpoint (frágil, olvidable).
  
CON AUP:
  AUP_SCOPE garantiza aislamiento estructural:
    - Vigilante tiene scope SOLO en su tenant
    - Operación fuera de scope → denegada por arquitectura
    - Data leak imposible por diseño
```

**Valor:** Seguridad multi-tenant nativa (no se puede "olvidar" validar).

### **4. Escalado Horizontal (Monetización por Tenant)**

```
MODELO DE NEGOCIO:
  Plan Free: 1 condominio, 10 residentes, QR 3 días
  Plan Pro: 5 condominios, 100 residentes, QR 30 días
  Plan Enterprise: 20 condominios, 1000 residentes, QR 365 días

SIN AUP:
  Límites hardcoded (if condominios > 5: raise Error)
  Cambiar plan requiere redeploy.

CON AUP:
  AUP_GOV con políticas dinámicas:
    - Cambiar plan = cambiar políticas en BD
    - No requiere redeploy
    - Auditable (quién cambió plan cuándo)
```

**Valor:** Monetización estructural (escalado sin código).

### **5. Incidentes Contenibles (Respuesta Rápida)**

```
INCIDENTE: QR clonado usado por persona no autorizada

SIN AUP:
  - Detección manual (vigilante debe recordar quién vio antes)
  - Revocación lenta (llamar a admin, admin llama a soporte)
  - Sin auditoría (no hay registro de quién revocó)

CON AUP:
  - Detección automática (AUP valida QR ya usado)
  - Revocación instantánea (admin tiene authority)
  - Auditoría completa (AUP_EVENT registra todo)
```

**Valor:** Respuesta a incidentes en segundos, no horas.

---

## 🏆 VALOR GENERADO (COMPARACIÓN SIN/CON AUP)

### **Dimensión 1: Seguridad**

| Aspecto | SIN AUP | CON AUP |
|---------|---------|---------|
| **Suplantación de identidad** | Password débil, no revocable | Credencial revocable, vigencia explícita |
| **Acceso no autorizado** | Validación manual (olvidable) | AUP_SCOPE bloquea por arquitectura |
| **QR clonado** | Detección manual | Sistema detecta uso múltiple automáticamente |
| **Responsabilidad** | Logs alterables | AUP_EVENT inmutable (no repudio) |

### **Dimensión 2: Operación**

| Aspecto | SIN AUP | CON AUP |
|---------|---------|---------|
| **Agregar condominio** | Deploy de código | Crear tenant (sin código) |
| **Cambiar límites** | Redeploy de backend | Cambiar policy en BD (dinámico) |
| **Revocar acceso** | Llamar a soporte | Admin revoca con authority (instantáneo) |
| **Auditoría** | Query SQL manual | AUP_EVENT con UI de búsqueda |

### **Dimensión 3: Escalado**

| Aspecto | SIN AUP | CON AUP |
|---------|---------|---------|
| **Monetización** | Límites hardcoded por plan | AUP_GOV con políticas por tenant |
| **Multi-tenant** | Validación manual en cada endpoint | AUP_SCOPE nativo (arquitectura) |
| **Gobierno** | Rol "admin" monolítico | AUP_GOV con authorities distribuidas |
| **Trazabilidad** | Feature opcional | AUP_EVENT transversal (obligatorio) |

---

## 🔒 DIFÍCIL DE REPLICAR SIN GRAFO AUP

### **Razón 1: Separación de Planos**

```
COMPETIDOR intenta replicar:
  "Voy a agregar roles y permisos"

PROBLEMA:
  Roles mezclan gobierno con operación.
  No hay separación entre:
    - Quién puede crear (gobierno)
    - Quién puede ejecutar (operación)

AUP:
  AUP_GOV es plano separado de AUP_SCOPE.
  Gobierno precede operación (policy-first).
  
RESULTADO:
  Competidor tiene permisos frágiles (hardcoded).
  AUP tiene gobierno estructural (declarativo).
```

### **Razón 2: Trazabilidad Nativa vs Feature**

```
COMPETIDOR intenta replicar:
  "Voy a agregar logs"

PROBLEMA:
  Logs como feature → olvidable.
  Algunos endpoints registran, otros no.
  Logs alterables (admin puede borrar).

AUP:
  AUP_EVENT es nodo transversal (TODO declara a evento).
  Si no hay evento, no ocurrió (axioma).
  Evento es inmutable (append-only).

RESULTADO:
  Competidor tiene logs parciales, frágiles.
  AUP tiene trazabilidad estructural, garantizada.
```

### **Razón 3: Multi-Tenant por Diseño vs Parche**

```
COMPETIDOR intenta replicar:
  "Voy a agregar tenant_id a todas las tablas"

PROBLEMA:
  Validación manual en cada query (frágil).
  Un WHERE tenant_id = X olvidado → data leak.

AUP:
  AUP_SCOPE + AUP_TENANT como nodos estructurales.
  Scope SIEMPRE valida tenant (arquitectura).
  Data leak imposible por diseño.

RESULTADO:
  Competidor tiene multi-tenant frágil (manual).
  AUP tiene aislamiento nativo (estructural).
```

### **Razón 4: Gobierno Dinámico vs Hardcoded**

```
COMPETIDOR intenta replicar:
  "Voy a agregar if MAX_CONDOMINIOS > 5: raise Error"

PROBLEMA:
  Límites en código (cambiar requiere redeploy).
  No auditable (quién cambió límite).
  Un límite para todos (no personalizable).

AUP:
  AUP_GOV con políticas en BD (dinámico).
  Límites por tenant (personalizable).
  Cambios auditables (AUP_EVENT registra).

RESULTADO:
  Competidor tiene límites rígidos (operacional).
  AUP tiene gobierno flexible (estructural).
```

---

## 🎯 CONCLUSIÓN: AUP NO ES PRODUCTO, ES INFRAESTRUCTURA

### **Lo que parece (en superficie):**

```
"Sistema de control de accesos para condominios"
"App para generar QR de visitas"
"Software multi-tenant con roles"
```

### **Lo que realmente es (estructural):**

```
INFRAESTRUCTURA AUP aplicada a vertical residencial donde:

1. AUP_IDENTITY → Actor (residente, vigilante, visita)
2. AUP_CREDENTIAL → Prueba (password, QR, biometría)
3. AUP_SESSION → Contexto temporal (turno, sesión, visita)
4. AUP_SCOPE → Alcance espacial (unidad, condominio, global)
5. AUP_TENANT → Contenedor (condominio como universo aislado)
6. AUP_EVENT → Bitácora inmutable (auditoría forense)
7. AUP_GOV → Meta-poder (quién puede crear, limitar, revocar)
```

### **Por qué importa:**

**Competidor puede copiar features (UI de QR, registro de visitas).**

**Competidor NO puede copiar arquitectura estructural:**
- Separación de planos (gobierno vs operación)
- Trazabilidad nativa (evento transversal)
- Multi-tenant por diseño (scope arquitectural)
- Gobierno dinámico (políticas declarativas)

**AUP es ventaja estructural no replicable sin rediseño total.**

---

## 📐 PROYECCIÓN A OTRAS VERTICALES (MISMO GRAFO)

### **Si cambias de Residencial a Banking:**

```
AUP_IDENTITY → Cliente bancario (KYC)
AUP_CREDENTIAL → PIN + token OTP
AUP_SESSION → Sesión online (timeout 15 min)
AUP_SCOPE → Alcance en cuenta (lectura/escritura)
AUP_TENANT → Sucursal / producto financiero
AUP_EVENT → Transacción (auditable por regulador)
AUP_GOV → Política de riesgo (límites de transferencia)

MISMO GRAFO, DIFERENTE SEMÁNTICA.
```

### **Si cambias de Residencial a Healthcare:**

```
AUP_IDENTITY → Médico / paciente
AUP_CREDENTIAL → Badge RFID + biometría
AUP_SESSION → Turno clínico
AUP_SCOPE → Alcance en expediente (HIPAA)
AUP_TENANT → Hospital / clínica
AUP_EVENT → Acceso a expediente (auditable)
AUP_GOV → Política de privacidad (quién ve qué)

MISMO GRAFO, DIFERENTE SEMÁNTICA.
```

**Propiedad universal:** El grafo NO muta, solo se proyecta.

---

## 🔮 IMPLICACIÓN FINAL

**AUP no es sistema de control de accesos.**

**AUP es arquitectura estructural que:**
- Se proyecta a control de accesos (esta verticalización)
- Se proyecta a banking, healthcare, OT, legal, gobierno
- Mantiene los mismos 7 nodos (identidad, credencial, sesión, scope, tenant, evento, gobierno)
- Garantiza las mismas propiedades (trazabilidad, poder explícito, aislamiento, gobierno)

**Esto hace que AUP sea:**
1. **Portable:** Un dominio → múltiples dominios sin reescribir
2. **Defendible:** Competencia puede copiar features, no arquitectura
3. **Escalable:** Agregar tenant = nueva instancia, no código
4. **Auditable:** Evento transversal garantiza compliance
5. **Gobernable:** Poder explícito, dinámico, revocable

**Esto es AUP: Infraestructura estructural de propósito universal, aplicada verticalmente.**

═══════════════════════════════════════════════════════════════════════════
