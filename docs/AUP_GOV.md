# ═══════════════════════════════════════════════════════════════════════════
# PASO 4: AUP_GOV - Gobierno de Plataforma
# ═══════════════════════════════════════════════════════════════════════════

## 📐 DECLARACIÓN AUP

### **AUP_GOV (Gobierno)**

Entidad estructural que define y controla el **PODER sistémico**:  
quién puede crear, delegar, limitar, suspender o auditar capacidades dentro de la plataforma.

**AUP_GOV NO ES:**
- ❌ Un rol operativo (como ADMIN_CONDOMINIO)
- ❌ Permisos hardcodeados
- ❌ RBAC clásico mezclado con lógica de negocio

**AUP_GOV ES:**
- ✅ Plano superior de control (meta-poder)
- ✅ Gobierno explícito y auditable
- ✅ Separación entre poder y operación
- ✅ Base para escalado y monetización

---

## 🧱 SUB-ENTIDADES DE AUP_GOV

### **1. AUP_AUTHORITY (Autoridad de Gobierno)**

Actor con potestad declarada para gobernar.

```
AUP_AUTHORITY {
    authority_id:   STRING          # Identificador único
    identity_id:    AUP_IDENTITY    # Quién tiene la autoridad
    tipo:           AUTHORITY_TYPE  # GLOBAL | FIRST_TIER
    estado:         STATUS          # ACTIVO | SUSPENDIDO | REVOCADO
    tenant_id:      AUP_TENANT?     # NULL si GLOBAL, tenant_id si FIRST_TIER
    metadata:       JSON
    created_at:     DATETIME
    revoked_at:     DATETIME?
}
```

**Tipos:**
- **GLOBAL:** Autoridad sobre toda la plataforma (ej: MSP_ADMIN global)
- **FIRST_TIER:** Autoridad sobre un tenant específico (ej: Dueño de Condominio)

**Axioma:** Solo AUP_AUTHORITY puede crear o delegar poder.

---

### **2. AUP_POLICY (Política de Gobierno)**

Regla declarativa que gobierna límites y delegaciones.

```
AUP_POLICY {
    policy_id:        STRING          # Identificador único
    nombre:           STRING          # Nombre declarativo
    ámbito:           SCOPE_TYPE      # GLOBAL | TENANT | SCOPE
    target_tenant_id: AUP_TENANT?     # NULL si GLOBAL
    
    # QUÉ gobierna
    accion_objetivo:  STRING          # crear_tenant, asignar_scope, generar_qr
    
    # LÍMITES estructurales
    limites:          JSON            # {max_tenants: 10, max_qr_vigencia_dias: 7}
    
    # VIGENCIA
    valida_desde:     DATETIME
    valida_hasta:     DATETIME?
    
    estado:           STATUS
    metadata:         JSON
}
```

**Ámbitos:**
- **GLOBAL:** Aplica a toda la plataforma
- **TENANT:** Aplica a un tenant específico
- **SCOPE:** Aplica a scopes con cierto nivel

**Ejemplos:**
1. `{"max_count": 5}` → máximo 5 tenants por first tier
2. `{"max_dias_vigencia": 7}` → QRs válidos hasta 7 días
3. `{"max_usuarios": 100}` → máximo 100 usuarios por tenant

**Axioma:** La política precede a la operación (policy-first).

---

### **3. AUP_DELEGATION (Delegación de Poder)**

Relación que transfiere poder desde una autoridad a identidades o scopes.

```
AUP_DELEGATION {
    delegation_id:        STRING          # Identificador único
    authority_id:         AUP_AUTHORITY   # Quién delega
    
    # A QUIÉN se delega (mutuamente excluyente)
    target_identity_id:   AUP_IDENTITY?   # Usuario específico
    target_scope_id:      AUP_SCOPE?      # Scope específico
    
    # QUÉ se delega
    permisos_delegados:   JSON            # ["crear_tenant", "asignar_scope"]
    
    # VIGENCIA
    valida_desde:         DATETIME
    valida_hasta:         DATETIME?
    
    estado:               STATUS
    metadata:             JSON
}
```

**Axiomas:**
1. Todo poder delegado es **explícito** (lista de permisos)
2. Todo poder delegado es **acotado** (tiempo/alcance)
3. Todo poder delegado es **revocable**

---

## 🔗 RELACIONES AUP

```
AUP_IDENTITY --tiene→ AUP_AUTHORITY
AUP_AUTHORITY --define→ AUP_POLICY
AUP_AUTHORITY --crea→ AUP_DELEGATION
AUP_DELEGATION --otorga_poder_a→ AUP_IDENTITY | AUP_SCOPE
AUP_POLICY --limita→ AUP_SCOPE | AUP_TENANT
AUP_GOV --genera→ AUP_EVENT (toda acción de gobierno)
```

---

## 📜 AXIOMAS DE AUP_GOV (NO NEGOCIABLES)

### **1. PODER EXPLÍCITO**
Ninguna identidad puede crear o ampliar poder sin AUP_GOV.

### **2. DELEGACIÓN ACOTADA**
Todo poder delegado tiene límites (tiempo, alcance, acciones).

### **3. SEPARACIÓN DE PLANOS**
AUP_GOV no ejecuta operaciones; solo autoriza estructuras.

### **4. AUDITORÍA OBLIGATORIA**
Toda acción de gobierno genera AUP_EVENT.

### **5. POLICY-FIRST**
El gobierno precede a la operación.  
Se evalúan políticas ANTES de permitir acción.

### **6. REVOCABILIDAD**
Todo poder puede ser revocado instantáneamente.

---

## 🗂️ MAPEO: CONCEPTO AUP → CÓDIGO

| Concepto AUP | Implementación | Archivo |
|--------------|----------------|---------|
| AUP_AUTHORITY | Authority (SQLAlchemy model) | `backend/db/models.py` |
| AUP_POLICY | Policy (SQLAlchemy model) | `backend/db/models.py` |
| AUP_DELEGATION | Delegation (SQLAlchemy model) | `backend/db/models.py` |
| AuthorityType | GLOBAL, FIRST_TIER enum | `backend/core/gov/__init__.py` |
| PolicyScope | GLOBAL, TENANT, SCOPE enum | `backend/core/gov/__init__.py` |
| GovStatus | ACTIVO, SUSPENDIDO, REVOCADO enum | `backend/core/gov/__init__.py` |
| crear_authority() | Función estructural | `backend/core/gov/authority.py` |
| evaluar_politica() | Evaluador central | `backend/core/gov/policy.py` |
| delegar_poder() | Función estructural | `backend/core/gov/delegation.py` |
| *_con_evento() | Integraciones con EVENT | `backend/core/gov/integration.py` |

---

## 🔑 FUNCIONES CENTRALES

### **1. crear_authority()**

```python
def crear_authority(
    db: Session,
    identity: Usuario,
    tipo: AuthorityType,
    tenant_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Authority
```

**Pregunta:** ¿Quién tiene poder para gobernar?  
**NO pregunta:** ¿Qué puede hacer operativamente?  
**SÍ declara:** Esta identidad tiene autoridad de tipo X sobre Y

---

### **2. evaluar_politica()**

```python
def evaluar_politica(
    db: Session,
    accion: str,
    tenant_id: Optional[str] = None,
    valor_actual: Optional[Any] = None,
    metadata: Optional[dict] = None
) -> tuple[bool, Optional[str]]
```

**Pregunta:** ¿Esta acción está permitida según políticas activas?  
**NO pregunta:** ¿Debo permitir esto? (eso es autorización operativa)  
**SÍ evalúa:** Límites estructurales definidos en políticas

**Flujo:**
1. Buscar políticas aplicables (TENANT + GLOBAL)
2. Evaluar límites de cada política
3. Si alguna política DENIEGA → DENEGADO
4. Si todas PERMITEN → PERMITIDO
5. Si no hay políticas → DENEGADO (safe by default)

---

### **3. delegar_poder()**

```python
def delegar_poder(
    db: Session,
    authority: Authority,
    permisos: list[str],
    target_identity_id: Optional[str] = None,
    target_scope_id: Optional[str] = None,
    valida_desde: Optional[datetime] = None,
    valida_hasta: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Delegation
```

**Pregunta:** ¿Quién recibe qué poder y hasta cuándo?  
**NO pregunta:** ¿Puede ejecutar esta acción? (eso es operación)  
**SÍ declara:** Transferencia explícita de permisos con vigencia

---

## 🚀 CASOS DE USO

### **1. Crear First Tier (Dueño de Condominio)**

```python
# 1. Crear usuario first tier
usuario_first_tier = Usuario(
    usuario_id="ft_user123",
    nombre="Juan Pérez",
    email="juan@condominio.com",
    rol="ADMIN_CONDOMINIO"
)

# 2. Crear tenant (condominio)
condominio = Condominio(
    condominio_id="condo_a",
    nombre="Condominio Las Palmas"
)

# 3. Crear AUTHORITY para el first tier
authority = crear_authority_con_evento(
    db=db,
    ejecutor=admin_global,  # MSP_ADMIN
    session_token=token,
    identity=usuario_first_tier,
    tipo=AuthorityType.FIRST_TIER,
    tenant_id="condo_a"
)

# 4. Crear POLICY de límites para este first tier
policy = crear_policy_con_evento(
    db=db,
    ejecutor=admin_global,
    session_token=token,
    nombre="Límites Condominio A",
    ambito=PolicyScope.TENANT,
    accion_objetivo="crear_usuario",
    limites={"max_usuarios": 100},
    target_tenant_id="condo_a"
)
```

**Resultado:**
- Usuario `juan@condominio.com` tiene AUTHORITY sobre `condo_a`
- Puede crear usuarios, pero está limitado a 100 máximo
- Todo registrado con AUP_EVENT

---

### **2. Evaluar Política Antes de Crear Tenant**

```python
# First tier intenta crear su 6to tenant
# (política global: max 5 tenants)

permitido, motivo = evaluar_politica_con_evento(
    db=db,
    ejecutor=usuario_first_tier,
    session_token=token,
    accion="crear_tenant",
    tenant_id=None,  # Acción global
    valor_actual=5   # Ya tiene 5 tenants
)

if not permitido:
    # motivo: "Límite excedido: máximo 5 (actual: 5)"
    raise HTTPException(403, detail=motivo)

# Si permitido → crear tenant
```

**Flujo:**
1. Busca política con `accion_objetivo="crear_tenant"`
2. Encuentra: `{"max_count": 5}`
3. Compara: `valor_actual (5) >= max_count (5)` → DENEGADO
4. Registra evento con resultado=DENEGADO
5. Usuario no puede crear más tenants

---

### **3. Delegar Poder Temporalmente**

```python
# First tier delega permiso de "asignar_scope" a su admin
delegation = delegar_poder_con_evento(
    db=db,
    ejecutor=first_tier,
    session_token=token,
    authority=first_tier_authority,
    permisos=["asignar_scope", "crear_usuario"],
    target_identity_id="admin_local_123",
    valida_hasta=datetime.now() + timedelta(days=30)  # 30 días
)
```

**Resultado:**
- `admin_local_123` puede asignar scopes y crear usuarios
- Solo en `condo_a` (autoridad del first tier)
- Solo por 30 días
- Todo registrado con AUP_EVENT

---

### **4. Límite de Vigencia de QR**

```python
# Política global: QRs máximo 7 días de vigencia

# Usuario intenta generar QR con 10 días
permitido, motivo = evaluar_politica_con_evento(
    db=db,
    ejecutor=usuario,
    session_token=token,
    accion="generar_qr",
    tenant_id="condo_a",
    metadata={"dias_vigencia": 10}
)

# motivo: "Vigencia excedida: máximo 7 días (solicitado: 10)"
# permitido: False
```

**Integración en endpoint:**

```python
@router.post("/qr/generar/{visita_id}")
def generar_qr(visita_id: str, dias_vigencia: int, ...):
    # Evaluar política ANTES de generar
    permitido, motivo = evaluar_politica_con_evento(
        db, usuario, token,
        "generar_qr",
        tenant_id=visita.condominio_id,
        metadata={"dias_vigencia": dias_vigencia}
    )
    
    if not permitido:
        raise HTTPException(403, detail=motivo)
    
    # Si permitido → generar QR
    qr = generar_qr_service(visita_id, dias_vigencia)
    return qr
```

---

## 📊 COMPARACIÓN: SIN AUP_GOV vs CON AUP_GOV

### **SIN AUP_GOV (Hardcoded):**

```python
# Código hardcodeado
MAX_TENANTS_PER_USER = 5  # ¿Quién decide? ¿Cómo cambiar?

if usuario.tenants_count >= MAX_TENANTS_PER_USER:
    raise HTTPException(403, "Límite de tenants alcanzado")

# Problemas:
# - No auditable (no hay evento)
# - No dinámico (requiere redeploy)
# - No gobernable (no se puede revocar)
# - No escalable (un límite para todos)
```

### **CON AUP_GOV (Declarativo):**

```python
# Política declarativa en BD
policy = Policy(
    nombre="Límite First Tier Estándar",
    ambito=PolicyScope.GLOBAL,
    accion_objetivo="crear_tenant",
    limites={"max_count": 5}
)

# Evaluación estructural
permitido, motivo = evaluar_politica(
    db, "crear_tenant",
    valor_actual=usuario.tenants_count
)

# Ventajas:
# ✅ Auditable (genera AUP_EVENT)
# ✅ Dinámico (modificar política sin redeploy)
# ✅ Gobernable (revocar/modificar políticas)
# ✅ Escalable (políticas por tenant, usuario, scope)
```

---

## 💎 VENTAJAS DE AUP_GOV

### **1. Separación de Planos**
- **Plano de Gobierno:** Quién puede crear/delegar poder
- **Plano Operativo:** Quién puede ejecutar acciones

Admin de condominio ≠ Authority de gobierno

### **2. Escalabilidad Nativa**
- Políticas por tenant (límites específicos)
- Delegaciones temporales (30 días, 1 año)
- First tier con autonomía limitada

### **3. Monetización Preparada**
```python
# Plan Free: 1 tenant, 50 usuarios
policy_free = Policy(
    limites={"max_count": 1, "max_usuarios": 50}
)

# Plan Pro: 5 tenants, 200 usuarios
policy_pro = Policy(
    limites={"max_count": 5, "max_usuarios": 200}
)
```

### **4. Compliance y Auditoría**
- Histórico completo de quién creó qué poder
- Revocaciones trazables
- Evaluaciones de política registradas

### **5. Revocación Instantánea**
```python
# Revocar authority → pierde todo el poder
revocar_authority_con_evento(
    db, admin_global, token,
    authority_id="auth_abc123",
    motivo="Incumplimiento de términos"
)
# Efecto inmediato
```

---

## 🎯 INTEGRACIÓN CON PASOS ANTERIORES

### **PASO 1: AUP_SESSION** (Autenticación)
- Valida identidad (JWT)
- **AUP_GOV usa:** Saber QUIÉN ejecuta acción de gobierno

### **PASO 2: AUP_SCOPE** (Alcance Multi-Tenant)
- Valida alcance en tenant
- **AUP_GOV usa:** Limitar DÓNDE se puede delegar poder

### **PASO 3: AUP_EVENT** (Trazabilidad)
- Declara hechos inmutables
- **AUP_GOV usa:** Registrar TODA acción de gobierno

### **PASO 4: AUP_GOV** (Gobierno)
- Define poder sistémico
- **Habilita:** Escalado, monetización, compliance

---

## 🗄️ MODELO DE DATOS (Resumen)

### **Authority**
```python
class Authority(Base):
    __tablename__ = "authorities_gov"
    
    authority_id = Column(String, primary_key=True)
    identity_id = Column(String, ForeignKey("usuarios_exo.usuario_id"))
    tipo = Column(SQLEnum(AuthorityType))  # GLOBAL | FIRST_TIER
    tenant_id = Column(String, nullable=True)
    estado = Column(SQLEnum(GovStatus))
    created_at = Column(DateTime)
    revoked_at = Column(DateTime, nullable=True)
```

### **Policy**
```python
class Policy(Base):
    __tablename__ = "policies_gov"
    
    policy_id = Column(String, primary_key=True)
    nombre = Column(String)
    ambito = Column(SQLEnum(PolicyScope))  # GLOBAL | TENANT | SCOPE
    target_tenant_id = Column(String, nullable=True)
    accion_objetivo = Column(String)
    limites = Column(JSON)  # {"max_count": 5, "max_dias_vigencia": 7}
    valida_desde = Column(DateTime)
    valida_hasta = Column(DateTime, nullable=True)
    estado = Column(SQLEnum(GovStatus))
```

### **Delegation**
```python
class Delegation(Base):
    __tablename__ = "delegations_gov"
    
    delegation_id = Column(String, primary_key=True)
    authority_id = Column(String, ForeignKey("authorities_gov.authority_id"))
    target_identity_id = Column(String, nullable=True)
    target_scope_id = Column(String, nullable=True)
    permisos_delegados = Column(JSON)  # ["crear_tenant", "asignar_scope"]
    valida_desde = Column(DateTime)
    valida_hasta = Column(DateTime, nullable=True)
    estado = Column(SQLEnum(GovStatus))
```

---

## 📋 HELPERS DE CONSULTA

```python
# ¿Tiene authority activa?
tiene_authority(db, "user123", AuthorityType.GLOBAL)

# ¿Tiene permiso delegado?
tiene_permiso_delegado(db, "user123", "crear_tenant")

# Listar authorities de un tenant
listar_authorities(db, tipo=AuthorityType.FIRST_TIER, tenant_id="condo_a")

# Listar policies activas
listar_policies(db, accion_objetivo="generar_qr")
```

---

## ✅ RESULTADO FINAL - ARQUITECTURA AUP COMPLETA (4 PASOS)

```
✅ PASO 1: AUP_SESSION    → Identidad validada (JWT)
✅ PASO 2: AUP_SCOPE      → Alcance validado (multi-tenant)
✅ PASO 3: AUP_EVENT      → Hechos declarados (trazabilidad)
✅ PASO 4: AUP_GOV        → Poder controlado (gobierno)
```

### **Sistema ahora tiene:**
- ✅ Autenticación robusta
- ✅ Multi-tenant seguro
- ✅ Trazabilidad completa
- ✅ **Gobierno explícito y escalable**

### **Preparado para:**
- Escalado empresarial (first tier con límites)
- Monetización (planes con políticas diferentes)
- Compliance (auditoría de poder)
- Delegaciones temporales (autonomía limitada)

---

## 📚 LECCIÓN AUP FINAL

**Paradigma tradicional:**  
"Agregar roles de admin" → hardcoded, no escalable, no auditable.

**Paradigma AUP:**  
"Declarar AUP_GOV" → meta-poder estructural, auditable, gobernable.

**Esto es AUP:**
1. Declarar QUÉ existe (AUP_AUTHORITY, AUP_POLICY, AUP_DELEGATION)
2. Definir relaciones (AUTHORITY --define→ POLICY --limita→ OPERACIÓN)
3. Establecer axiomas (poder explícito, policy-first, revocabilidad)
4. Implementar como traducción directa (conceptos → código → eventos)

---

**PASO 4 completado. Sistema MSP_AXS con Gobierno de Plataforma.**

═══════════════════════════════════════════════════════════════════════════
