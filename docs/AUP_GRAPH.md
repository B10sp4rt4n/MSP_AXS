# ═══════════════════════════════════════════════════════════════════════════
# GRAFO AUP COMPLETO — ARQUITECTURA INTEGRAL MSP_AXS
# ═══════════════════════════════════════════════════════════════════════════

## DECLARACIÓN FUNDAMENTAL

Este documento define el **GRAFO AUP** del sistema MSP_AXS como estructura viva, cerrada y portable. No es un diagrama de implementación, es la **anatomía estructural** del sistema.

**Propiedad central:** Todo lo que existe en el sistema **vive en este grafo**. Si algo no puede ubicarse aquí, no pertenece al sistema.

---

## 🗺️ GRAFO AUP (REPRESENTACIÓN TEXTUAL)

```
                    ┌─────────────────┐
                    │  AUP_IDENTITY   │ ◄──── NODO RAÍZ
                    │   (¿Quién?)     │       (Todo parte de aquí)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ AUP_CREDENTIAL  │
                    │  (¿Con qué?)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  AUP_SESSION    │ ◄──── NODO CRÍTICO
                    │   (¿Cuándo?)    │       (Sin sesión, nada existe)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
             ┌──────│   AUP_SCOPE     │──────┐
             │      │   (¿Dónde?)     │      │
             │      └────────┬────────┘      │
             │               │                │
    ┌────────▼────────┐     │       ┌────────▼────────┐
    │   AUP_TENANT    │     │       │    AUP_GOV      │ ◄── NODO DE PODER
    │  (¿En qué?)     │     │       │  (¿Quién manda?)│     (Gobierna estructura)
    └─────────────────┘     │       └─────────────────┘
                             │                │
                    ┌────────▼────────────────▼────────┐
                    │       AUP_EVENT                  │ ◄── NODO TRANSVERSAL
                    │   (¿Qué pasó?)                   │     (Registra todo)
                    └──────────────────────────────────┘
```

---

## 📊 RELACIONES DIRECCIONALES (SEMÁNTICA EXPLÍCITA)

### **1. IDENTIDAD → CREDENCIAL → SESIÓN**

```
AUP_IDENTITY ──posee──▶ AUP_CREDENTIAL
  │ Dependencia: FUERTE
  │ Dirección: Identidad controla credenciales
  │ Si falla: No hay autenticación posible
  │ Semántica: "Una identidad posee credenciales para probar quién es"

AUP_CREDENTIAL ──valida──▶ AUP_SESSION
  │ Dependencia: FUERTE
  │ Dirección: Credencial válida crea sesión
  │ Si falla: Sistema queda cerrado (nadie puede entrar)
  │ Semántica: "Credencial válida habilita contexto temporal"

AUP_IDENTITY ──inicializa──▶ AUP_SESSION
  │ Dependencia: FUERTE
  │ Dirección: Identidad es dueña de sesión
  │ Si falla: No hay contexto de ejecución
  │ Semántica: "Toda sesión pertenece a una identidad"
```

### **2. SESIÓN → ALCANCE**

```
AUP_SESSION ──habilita──▶ AUP_SCOPE
  │ Dependencia: FUERTE
  │ Dirección: Sin sesión válida, no hay scope
  │ Si falla: Alcance queda indefinido (operación imposible)
  │ Semántica: "Sesión activa habilita alcance en tenant"

AUP_SESSION ──precede──▶ AUP_SCOPE
  │ Dependencia: TEMPORAL
  │ Dirección: Sesión debe existir ANTES que scope
  │ Si falla: Violación de orden estructural
  │ Semántica: "No hay alcance sin contexto temporal previo"
```

### **3. ALCANCE → TENANT**

```
AUP_SCOPE ──opera_en──▶ AUP_TENANT
  │ Dependencia: FUERTE
  │ Dirección: Scope siempre apunta a tenant
  │ Si falla: Operación sin contenedor (data leak)
  │ Semántica: "Scope define dónde ocurre la acción"

AUP_TENANT ──contiene──▶ AUP_SCOPE
  │ Dependencia: ESTRUCTURAL
  │ Dirección: Tenant agrupa scopes
  │ Si falla: Multi-tenancy colapsa
  │ Semántica: "Tenant es contenedor de alcances"
```

### **4. GOBIERNO → TODO**

```
AUP_GOV ──gobierna──▶ AUP_TENANT
  │ Dependencia: META-PODER
  │ Dirección: Gobierno decide quién puede crear/suspender tenants
  │ Si falla: Escalado descontrolado (anyone can create)
  │ Semántica: "Gobierno controla existencia de tenants"

AUP_GOV ──gobierna──▶ AUP_SCOPE
  │ Dependencia: META-PODER
  │ Dirección: Gobierno decide límites de alcance
  │ Si falla: Scopes sin límites (users can escalate)
  │ Semántica: "Gobierno controla alcance de poder"

AUP_GOV ──gobierna──▶ AUP_IDENTITY
  │ Dependencia: META-PODER
  │ Dirección: Gobierno puede revocar identidades
  │ Si falla: Identidades irrevocables (compliance risk)
  │ Semántica: "Gobierno controla ciclo de vida de identidades"

AUP_GOV ──precede──▶ OPERACIÓN
  │ Dependencia: POLICY-FIRST
  │ Dirección: Gobierno evalúa ANTES de permitir
  │ Si falla: Operaciones sin límites
  │ Semántica: "Política precede ejecución"
```

### **5. EVENTO ← TODO**

```
AUP_SESSION ──declara──▶ AUP_EVENT
  │ Dependencia: AUDITORÍA
  │ Dirección: Sesión activa declara evento al crear/cerrar
  │ Si falla: Login/logout sin trazabilidad
  │ Semántica: "Toda sesión genera hechos auditables"

AUP_SCOPE ──declara──▶ AUP_EVENT
  │ Dependencia: AUDITORÍA
  │ Dirección: Scope asignado declara evento
  │ Si falla: Cambios de alcance sin auditoría
  │ Semántica: "Toda operación en scope genera evento"

AUP_GOV ──declara──▶ AUP_EVENT
  │ Dependencia: AUDITORÍA
  │ Dirección: Gobierno declara cada acción de poder
  │ Si falla: Poder sin trazabilidad (dictadura)
  │ Semántica: "Todo ejercicio de poder genera evento"

AUP_TENANT ──declara──▶ AUP_EVENT
  │ Dependencia: AUDITORÍA
  │ Dirección: Tenant declara creación/suspensión
  │ Si falla: Tenants sin historial
  │ Semántica: "Toda mutación de tenant genera evento"

* (TODO) ──declara──▶ AUP_EVENT
  │ Dependencia: UNIVERSAL
  │ Dirección: Toda operación declara evento
  │ Si falla: Sistema opaco (no auditable)
  │ Semántica: "Si no hay evento, no ocurrió"
```

---

## 🧬 TABLA DE NODOS (ANATOMÍA ESTRUCTURAL)

| **Nodo**         | **Función Estructural**                     | **Dependencias Upstream**           | **Qué Rompe Si Falla**                                |
|------------------|---------------------------------------------|-------------------------------------|-------------------------------------------------------|
| AUP_IDENTITY     | Declarar QUIÉN (origen de toda acción)      | Ninguna (RAÍZ)                      | Todo (sin identidad no hay sistema)                   |
| AUP_CREDENTIAL   | Validar autenticidad de identidad           | AUP_IDENTITY                        | Autenticación (acceso imposible)                      |
| AUP_SESSION      | Establecer contexto temporal de ejecución   | AUP_IDENTITY, AUP_CREDENTIAL        | Operaciones sin contexto (todo se detiene)            |
| AUP_SCOPE        | Definir alcance espacial en tenant          | AUP_SESSION, AUP_TENANT             | Multi-tenancy (data leaks, acceso cruzado)            |
| AUP_TENANT       | Contenedor de datos/operaciones             | AUP_GOV (para creación)             | Aislamiento (mezcla de datos entre clientes)          |
| AUP_GOV          | Controlar poder sistémico (meta-poder)      | AUP_IDENTITY (para asignar)         | Gobierno (escalado sin límites, anyone can create)    |
| AUP_EVENT        | Declarar hechos inmutables (auditoría)      | TODO (recibe de todos)              | Trazabilidad (sistema opaco, no auditable)            |

---

## 🎯 AXIOMAS DEL GRAFO

### **AXIOMA 1: NODO RAÍZ**

```
NODO: AUP_IDENTITY
RAZÓN: Todo parte de "quién"
PROPIEDAD: Sin identidad, no hay sesión, scope, evento ni gobierno
IMPLICACIÓN: Identidad es el único nodo sin dependencias upstream
```

**Consecuencia:** Si borras identidad, todo lo downstream colapsa.

### **AXIOMA 2: NODO CRÍTICO**

```
NODO: AUP_SESSION
RAZÓN: Es el paso obligatorio entre autenticación y operación
PROPIEDAD: Sin sesión, no hay contexto de ejecución
IMPLICACIÓN: Si sesión falla, sistema queda cerrado (nadie opera)
```

**Consecuencia:** Sesión es el cuello de botella estructural (el más crítico).

### **AXIOMA 3: NODO TRANSVERSAL**

```
NODO: AUP_EVENT
RAZÓN: TODO declara eventos (universal)
PROPIEDAD: Es el único nodo que recibe de todos los demás
IMPLICACIÓN: Evento es el testigo de TODO lo que ocurre
```

**Consecuencia:** Si evento falla, sistema se vuelve opaco (no auditable).

### **AXIOMA 4: NODO DE PODER**

```
NODO: AUP_GOV
RAZÓN: Gobierna la estructura (meta-poder)
PROPIEDAD: Puede crear, limitar, suspender otros nodos (tenant, scope, identity)
IMPLICACIÓN: Es el único nodo que PRECEDE operaciones (policy-first)
```

**Consecuencia:** Si gobierno falla, sistema queda sin límites (escalado descontrolado).

---

## 🔗 DEPENDENCIAS EN CASCADA

### **Cascada de Fallo 1: Identidad**

```
AUP_IDENTITY falla
  └──▶ AUP_CREDENTIAL sin dueño
       └──▶ AUP_SESSION sin origen
            └──▶ AUP_SCOPE sin contexto
                 └──▶ AUP_EVENT sin actor
                      └──▶ SISTEMA COLAPSA
```

### **Cascada de Fallo 2: Sesión**

```
AUP_SESSION falla
  └──▶ AUP_SCOPE sin habilitación
       └──▶ OPERACIÓN imposible
            └──▶ AUP_EVENT sin contexto temporal
                 └──▶ AUDITORÍA ROTA
```

### **Cascada de Fallo 3: Gobierno**

```
AUP_GOV falla
  └──▶ AUP_TENANT sin límites (anyone creates)
       └──▶ AUP_SCOPE sin control (anyone escalates)
            └──▶ ESCALADO DESCONTROLADO
                 └──▶ MONETIZACIÓN IMPOSIBLE
```

### **Cascada de Fallo 4: Evento**

```
AUP_EVENT falla
  └──▶ OPERACIONES sin trazabilidad
       └──▶ AUDITORÍA imposible
            └──▶ COMPLIANCE ROTA
                 └──▶ SISTEMA OPACO (no confiable)
```

---

## 🌐 PORTABILIDAD DEL GRAFO

### **Por Qué Este Grafo Es Universal**

#### **1. Independencia de Dominio**

```
DOMINIO: Banca
  AUP_IDENTITY → Cliente bancario
  AUP_SESSION  → Sesión de banca online
  AUP_SCOPE    → Alcance en cuenta específica
  AUP_TENANT   → Sucursal / producto financiero
  AUP_GOV      → Regulación (límites de transferencia, KYC)
  AUP_EVENT    → Transacción registrada (compliance)

DOMINIO: OT (Operational Technology)
  AUP_IDENTITY → Operador industrial
  AUP_SESSION  → Turno de trabajo
  AUP_SCOPE    → Alcance en planta/área
  AUP_TENANT   → Sitio industrial
  AUP_GOV      → Política de seguridad (quién opera qué máquina)
  AUP_EVENT    → Acción en SCADA (auditoría de operación)

DOMINIO: Legal
  AUP_IDENTITY → Abogado / cliente
  AUP_SESSION  → Sesión en sistema de casos
  AUP_SCOPE    → Alcance en expediente
  AUP_TENANT   → Bufete / cliente corporativo
  AUP_GOV      → Control de acceso a documentos sensibles
  AUP_EVENT    → Modificación de documento (prueba legal)

DOMINIO: Gobierno
  AUP_IDENTITY → Funcionario público
  AUP_SESSION  → Sesión en sistema estatal
  AUP_SCOPE    → Alcance en dependencia
  AUP_TENANT   → Municipio / estado
  AUP_GOV      → Política de transparencia (quién puede ver qué)
  AUP_EVENT    → Acto administrativo (trazabilidad pública)
```

**Propiedad común:** El grafo NO cambia, solo cambia la semántica de los nodos.

#### **2. Cerrado Estructuralmente**

**Definición:** El grafo no necesita nodos nuevos para expresar cualquier caso.

**Prueba:**
- ¿Necesitas autenticación? → AUP_SESSION
- ¿Necesitas multi-tenancy? → AUP_TENANT + AUP_SCOPE
- ¿Necesitas auditoría? → AUP_EVENT
- ¿Necesitas gobierno? → AUP_GOV
- ¿Necesitas límites? → AUP_GOV + AUP_POLICY
- ¿Necesitas delegación? → AUP_GOV + AUP_DELEGATION

**Consecuencia:** El grafo es COMPLETO (no necesita parches).

#### **3. Expansible Sin Mutación**

**Propiedad:** Agregar casos NO modifica el grafo, solo agrega instancias.

```
CASO NUEVO: Multi-factor authentication (MFA)
  ┌────────────────────────────────────────────┐
  │ ¿Dónde vive en el grafo?                   │
  │ → AUP_CREDENTIAL (segundo factor)          │
  │ → AUP_SESSION (requiere validación dual)   │
  │ → AUP_EVENT (registra intento MFA)         │
  └────────────────────────────────────────────┘

CASO NUEVO: Single Sign-On (SSO)
  ┌────────────────────────────────────────────┐
  │ ¿Dónde vive en el grafo?                   │
  │ → AUP_IDENTITY (identidad federada)        │
  │ → AUP_SESSION (sesión propagada)           │
  │ → AUP_SCOPE (alcance heredado)             │
  │ → AUP_EVENT (registra propagación)         │
  └────────────────────────────────────────────┘

CASO NUEVO: Monetización (planes Free/Pro)
  ┌────────────────────────────────────────────┐
  │ ¿Dónde vive en el grafo?                   │
  │ → AUP_GOV (política con límites)           │
  │   - Plan Free: max_tenants=1               │
  │   - Plan Pro: max_tenants=5                │
  │ → AUP_EVENT (registra upgrade)             │
  └────────────────────────────────────────────┘
```

**Consecuencia:** Grafo estable a través de cambios de negocio.

---

## 🔒 PROPIEDADES EMERGENTES DEL GRAFO

### **Propiedad 1: Inversión de Control**

```
SIN GRAFO:
  Backend decide si usuario puede crear tenant (hardcoded)

CON GRAFO:
  AUP_GOV decide si usuario puede crear tenant (declarado)
  Backend consulta grafo (inversión de control)
```

**Beneficio:** Gobierno externo al código (configurable, auditable).

### **Propiedad 2: Trazabilidad Nativa**

```
SIN GRAFO:
  Evento es "feature" (se agrega después)

CON GRAFO:
  Evento es NODO TRANSVERSAL (todo declara a evento)
  Auditoría es propiedad del grafo, no feature
```

**Beneficio:** Trazabilidad estructural (no se puede "olvidar" registrar).

### **Propiedad 3: Escalabilidad Declarativa**

```
SIN GRAFO:
  Límites en código (if max_tenants > 5: raise Error)

CON GRAFO:
  Límites en AUP_GOV (política declarativa)
  Backend evalúa política (desacoplado)
```

**Beneficio:** Cambiar límites sin redeploy.

### **Propiedad 4: Tolerancia a Fallos**

```
Si AUP_EVENT falla temporalmente:
  ┌────────────────────────────────────┐
  │ Sistema sigue operando             │
  │ Eventos se encolan                 │
  │ Se recuperan al restaurar evento   │
  └────────────────────────────────────┘

Si AUP_SESSION falla:
  ┌────────────────────────────────────┐
  │ Sistema cierra acceso              │
  │ Operaciones detenidas              │
  │ Se reactiva al restaurar sesión    │
  └────────────────────────────────────┘
```

**Beneficio:** Grafo define qué es crítico y qué es degradable.

---

## 🧪 PREGUNTAS DE VALIDACIÓN DEL GRAFO

### **1. ¿Puedo crear un tenant sin sesión?**

```
AUP_SESSION ──habilita──▶ AUP_SCOPE ──opera_en──▶ AUP_TENANT
RESPUESTA: NO (sesión precede tenant)
RAZÓN: Sin sesión, no hay contexto de ejecución
```

### **2. ¿Puedo tener scope sin tenant?**

```
AUP_SCOPE ──opera_en──▶ AUP_TENANT
RESPUESTA: NO (scope siempre apunta a tenant)
RAZÓN: Scope sin tenant → data leak
```

### **3. ¿Puedo revocar identidad sin gobierno?**

```
AUP_GOV ──gobierna──▶ AUP_IDENTITY
RESPUESTA: SÍ (gobierno NO es obligatorio para CRUD básico)
PERO: Sin gobierno, no hay límites de revocación
RAZÓN: Gobierno es meta-poder, no poder operativo
```

### **4. ¿Puedo tener operación sin evento?**

```
* (TODO) ──declara──▶ AUP_EVENT
RESPUESTA: NO (todo declara evento)
RAZÓN: Si no hay evento, no ocurrió (axioma transversal)
```

### **5. ¿Qué pasa si AUP_GOV no existe?**

```
SIN AUP_GOV:
  ┌────────────────────────────────────┐
  │ Sistema funciona                    │
  │ PERO: sin límites                   │
  │ PERO: sin gobierno                  │
  │ PERO: no escalable                  │
  └────────────────────────────────────┘

CON AUP_GOV:
  ┌────────────────────────────────────┐
  │ Sistema funciona CON límites        │
  │ Sistema gobernable                  │
  │ Sistema monetizable                 │
  └────────────────────────────────────┘
```

**Conclusión:** Gobierno es opcional para MVP, obligatorio para producción.

---

## 📐 REGLAS DE EVOLUCIÓN DEL GRAFO

### **Regla 1: No Agregar Nodos Sin Justificación Estructural**

```
MAL:
  "Necesito notificaciones"
  → Agrego nodo AUP_NOTIFICATION

BIEN:
  "Necesito notificaciones"
  → AUP_EVENT genera notificación (observer pattern)
  → No necesita nodo nuevo
```

### **Regla 2: Todo Nuevo Nodo Debe Tener Relación Bidireccional**

```
MAL:
  AUP_X ──usa──▶ AUP_Y (relación unidireccional)
  ¿Y declara a EVENT? ¿Y gobierna GOV?

BIEN:
  AUP_X ──usa──▶ AUP_Y
  AUP_Y ──declara──▶ AUP_EVENT
  AUP_GOV ──gobierna──▶ AUP_X
```

### **Regla 3: Todo Nodo Debe Responder "¿Qué Rompe Si Fallo?"**

```
Si respuesta es "nada", el nodo NO es estructural (es feature).
Si respuesta es "todo colapsa", el nodo es CRÍTICO.
Si respuesta es "sistema opaco", el nodo es TRANSVERSAL.
Si respuesta es "sin límites", el nodo es GOBIERNO.
```

---

## 🏛️ APLICABILIDAD FUERA DE MSP_AXS

### **Caso 1: Sistema Bancario**

```
GRAFO APLICADO:
  AUP_IDENTITY → Cliente (KYC validado)
  AUP_SESSION  → Sesión online (OTP validado)
  AUP_SCOPE    → Alcance en cuenta (lectura/escritura)
  AUP_TENANT   → Sucursal / producto (cuenta corriente, inversión)
  AUP_GOV      → Regulación (límites de transferencia diaria)
  AUP_EVENT    → Transacción (auditable por banco central)

VENTAJA:
  Compliance nativo (todo evento es auditable)
  Límites dinámicos (gobierno puede cambiar límites sin redeploy)
  Multi-tenant (banco opera múltiples sucursales)
```

### **Caso 2: Sistema de Salud**

```
GRAFO APLICADO:
  AUP_IDENTITY → Médico / paciente
  AUP_SESSION  → Sesión clínica (turno)
  AUP_SCOPE    → Alcance en expediente (solo su especialidad)
  AUP_TENANT   → Hospital / clínica
  AUP_GOV      → Política HIPAA (quién ve qué datos sensibles)
  AUP_EVENT    → Acceso a expediente (auditable por regulación)

VENTAJA:
  Privacidad nativa (scope limita alcance)
  Auditoría médica (todo acceso registrado)
  Multi-hospital (cada hospital es tenant)
```

### **Caso 3: Sistema Industrial (OT)**

```
GRAFO APLICADO:
  AUP_IDENTITY → Operador / técnico
  AUP_SESSION  → Turno de trabajo
  AUP_SCOPE    → Alcance en planta (área 1, área 2)
  AUP_TENANT   → Sitio industrial (planta A, planta B)
  AUP_GOV      → Política de seguridad (quién opera máquina crítica)
  AUP_EVENT    → Acción en SCADA (auditable por seguridad)

VENTAJA:
  Seguridad nativa (gobierno controla acceso a máquinas)
  Trazabilidad total (toda acción en SCADA registrada)
  Multi-sitio (cada planta es tenant)
```

---

## 🎓 CONCLUSIÓN: POR QUÉ ESTE GRAFO EVITA PARCHES FUTUROS

### **1. Cerrado Estructuralmente**

```
El grafo tiene 7 nodos que cubren:
  - Identidad (quién)
  - Autenticación (con qué)
  - Contexto (cuándo)
  - Alcance (dónde)
  - Contenedor (en qué)
  - Poder (quién manda)
  - Auditoría (qué pasó)

NO HAY casos que no quepan en estos 7 nodos.
```

### **2. Relaciones Explícitas**

```
Cada relación es:
  - Direccional (A → B, no B → A)
  - Semántica (gobierna, habilita, declara)
  - Dependiente (fuerte, débil, temporal)

NO HAY ambigüedad sobre cómo interactúan los nodos.
```

### **3. Axiomas No Negociables**

```
RAÍZ: AUP_IDENTITY (todo parte de quién)
CRÍTICO: AUP_SESSION (sin sesión, nada opera)
TRANSVERSAL: AUP_EVENT (todo declara evento)
PODER: AUP_GOV (gobierno precede operación)

NO HAY casos donde estos axiomas no apliquen.
```

### **4. Portable a Cualquier Dominio**

```
Banca, salud, OT, legal, gobierno, educación, logística, etc.
TODOS usan los mismos 7 nodos.
SOLO cambia la semántica (qué representa cada nodo).

NO HAY dominios que requieran nodos nuevos.
```

### **5. Evoluciona Sin Mutar**

```
Nuevos casos (MFA, SSO, planes, etc.) se implementan
usando INSTANCIAS de nodos existentes, no nodos nuevos.

NO HAY mutación del grafo ante cambios de negocio.
```

---

## 🔮 USO DEL GRAFO EN FUTURO

### **1. Evaluación de Sistemas Externos**

```
PREGUNTA: "¿Este sistema legacy es compatible con AUP?"

MÉTODO:
  1. Identificar nodos en legacy (¿tiene identidad? ¿sesión? ¿scope?)
  2. Mapear relaciones (¿sesión habilita scope? ¿evento registra todo?)
  3. Buscar nodos faltantes (¿tiene gobierno? ¿tiene evento?)
  4. Declarar plan de migración (agregar nodos faltantes)

RESULTADO: Migración estructurada (no ad-hoc).
```

### **2. Manifiesto / Whitepaper**

```
El grafo AUP es la base para:
  - Explicar AUP a terceros (visual, claro)
  - Argumentar superioridad estructural vs sistemas ad-hoc
  - Demostrar portabilidad (mismo grafo, múltiples dominios)
  - Patentar arquitectura (cerrada, no trivial)
```

### **3. Certificación de Sistemas**

```
"Sistema certificado AUP" significa:
  ✅ Implementa los 7 nodos del grafo
  ✅ Respeta axiomas (raíz, crítico, transversal, poder)
  ✅ Relaciones direccionales correctas
  ✅ Auditoría nativa (evento transversal)
  ✅ Gobierno explícito (no hardcoded)
```

---

## 📜 RESUMEN EJECUTIVO

### **El Grafo AUP es:**

1. **Completo:** 7 nodos cubren todo caso
2. **Cerrado:** No necesita parches estructurales
3. **Portable:** Aplicable a cualquier dominio
4. **Explícito:** Relaciones direccionales y semánticas
5. **Axiomático:** Raíz, crítico, transversal, poder definidos
6. **Auditable:** Evento es nodo transversal (todo declara)
7. **Gobernable:** Gobierno es meta-poder (controla estructura)

### **Si algo no cabe en este grafo, no pertenece al sistema.**

### **Esto es AUP: Arquitectura que precede implementación.**

═══════════════════════════════════════════════════════════════════════════
