# Análisis de Abstracción: Patrón de Dominio Separado No Operativo

**Fecha:** 1 de enero de 2026  
**Contexto:** Análisis del Dominio Meta-Operativo v1.0 como patrón arquitectónico  
**Objetivo:** Identificar capacidades de abstracción y aplicación multidominio

---

## 1. Patrón Arquitectónico Identificado

### 1.1 Nombre del Patrón

**"Dominio Separado No Operativo" (DSNO)**

También conocido como: Meta-Domain, Cross-Cutting Concern Domain, Governance Layer

### 1.2 Definición Estructural

```
Un Dominio Separado No Operativo es una capa arquitectónica que:

1. NO opera dentro del contexto principal (tenant)
2. NO ejecuta lógica de negocio del dominio principal
3. NO tiene acceso a datos operativos
4. SÍ gestiona relaciones/configuraciones que habilitan operaciones
5. SÍ genera trazabilidad independiente
6. SÍ tiene autorización separada y más estricta
```

### 1.3 Características Estructurales

| Característica | Dominio Operativo | DSNO |
|----------------|-------------------|------|
| **Contexto de ejecución** | Dentro de tenant | Sin tenant activo |
| **Acceso a datos** | Tablas operativas (visitas, QRs) | Tablas de relación/configuración |
| **Autorización** | Por scope dentro de tenant | Authority específica (GLOBAL) |
| **tenant_id en eventos** | Siempre presente | Siempre NULL |
| **Middleware** | RequireTenant | Middleware separado |
| **Propósito** | Ejecutar negocio | Configurar/habilitar ejecución |

---

## 2. Abstracción del Código Implementado

### 2.1 Componentes Abstractos Identificados

#### A. **Validador de Authority Específica**

```python
# Patrón abstracto
def validate_domain_specific_authority(
    db: Session,
    actor_identity_id: str,
    required_authority_type: AuthorityType
) -> None:
    """
    Valida que el actor tenga authority del tipo requerido.
    
    Parámetro abstracto: required_authority_type
      - Para meta-operativo: GLOBAL
      - Para otros dominios: podría ser AUDIT, CONFIG, etc.
    """
    pass
```

**Aplicación multidominio:**
- Dominio de Auditoría: `validate_audit_authority()`
- Dominio de Configuración: `validate_config_authority()`
- Dominio de Billing: `validate_billing_authority()`

#### B. **Tabla de Relación Auditable**

```python
# Patrón abstracto
class AuditableRelation:
    """
    Tabla que registra relaciones con trazabilidad completa.
    
    Campos obligatorios:
      - relation_id
      - entity_a_id
      - entity_b_id
      - relation_type
      - created_by_identity_id
      - created_at
      - revoked (boolean)
      - revoked_by_identity_id
      - revoked_at
      - revocation_reason
    """
    pass
```

**Aplicación multidominio:**
- `identity_tenant_assignments` (meta-operativo) ✅
- `identity_role_assignments` (RBAC extendido)
- `tenant_feature_flags` (feature toggles)
- `tenant_billing_plans` (monetización)
- `identity_audit_delegations` (auditoría)

#### C. **Registro de Eventos Sin Tenant**

```python
# Patrón abstracto
def registrar_evento_dominio_separado(
    db: Session,
    actor: Usuario,
    session_token: str,
    domain_entity: str,        # Nombre del dominio
    entity_id: str,
    action: str,
    resultado: str,
    metadata: dict
) -> None:
    """
    Registra evento de un dominio separado.
    
    INVARIANTE: tenant_id = NULL
    
    Parámetro abstracto: domain_entity
      - META: "IDENTITY_TENANT_ASSIGNMENT"
      - AUDIT: "AUDIT_DELEGATION"
      - CONFIG: "SYSTEM_CONFIGURATION"
      - BILLING: "BILLING_PLAN_ASSIGNMENT"
    """
    registrar_evento(
        db=db,
        identity=actor,
        session_token=session_token,
        tenant_id=None,  # ← CRÍTICO: NULL para dominios separados
        entidad=domain_entity,
        entidad_id=entity_id,
        accion=action,
        resultado=resultado,
        metadata=metadata
    )
```

#### D. **Acciones CRUD con Validación Estricta**

```python
# Patrón abstracto
class DomainAction:
    """
    Acción de un dominio separado.
    
    Estructura:
      1. Validar authority específica
      2. Validar existencia de entidades
      3. Validar reglas de negocio del dominio
      4. Ejecutar acción (sin contexto de tenant)
      5. Registrar evento (tenant_id=NULL)
      6. Retornar resultado
    """
    
    @staticmethod
    def execute(db, actor, params):
        # 1. Authority
        validate_domain_authority(db, actor)
        
        # 2. Entidades
        validate_entities_exist(db, params)
        
        # 3. Reglas
        validate_domain_rules(db, params)
        
        # 4. Acción
        result = perform_action(db, params)
        
        # 5. Evento
        registrar_evento_dominio(db, actor, result)
        
        # 6. Retorno
        return result
```

---

## 3. Capacidades Multidominio Identificadas

### 3.1 Dominio de Auditoría (DSNO-AUDIT)

**Propósito:** Gestionar delegaciones temporales de capacidad de auditoría.

**Tabla de relación:**
```sql
CREATE TABLE audit_delegations (
    delegation_id VARCHAR(64) PRIMARY KEY,
    auditor_identity_id VARCHAR(64) NOT NULL,  -- Quién audita
    target_tenant_id VARCHAR(64) NOT NULL,     -- Qué tenant
    audit_scope VARCHAR(32) NOT NULL,          -- read_events | read_all | export
    delegated_by_identity_id VARCHAR(64) NOT NULL,
    delegated_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_by_identity_id VARCHAR(64) NULL,
    revoked_at TIMESTAMP NULL
);
```

**Authority requerida:** `AUDIT_ADMIN` (nueva)

**Acciones:**
- `delegate_audit_access()` - Otorgar acceso temporal de auditoría
- `revoke_audit_access()` - Revocar acceso de auditoría
- `list_audit_delegations()` - Listar auditorías activas

**Eventos:**
- `entidad = "AUDIT_DELEGATION"`
- `tenant_id = NULL`

**Casos de uso:**
- Auditor externo necesita revisar eventos de un tenant por 48 horas
- Compliance officer necesita exportar logs de múltiples tenants
- Internal audit temporal sin acceso operativo

### 3.2 Dominio de Configuración Global (DSNO-CONFIG)

**Propósito:** Gestionar configuraciones que afectan múltiples tenants.

**Tabla de relación:**
```sql
CREATE TABLE system_configurations (
    config_id VARCHAR(64) PRIMARY KEY,
    config_key VARCHAR(128) NOT NULL UNIQUE,
    config_value JSON NOT NULL,
    config_scope VARCHAR(32) NOT NULL,  -- GLOBAL | TENANT_GROUP | TENANT
    target_tenant_id VARCHAR(64) NULL,
    set_by_identity_id VARCHAR(64) NOT NULL,
    set_at TIMESTAMP NOT NULL,
    previous_value JSON NULL,
    effective_from TIMESTAMP NOT NULL,
    effective_until TIMESTAMP NULL
);
```

**Authority requerida:** `CONFIG_ADMIN` (nueva)

**Acciones:**
- `set_global_config()` - Establecer configuración global
- `set_tenant_config()` - Override de configuración por tenant
- `list_configurations()` - Listar configuraciones activas
- `revert_configuration()` - Revertir a valor anterior

**Eventos:**
- `entidad = "SYSTEM_CONFIGURATION"`
- `tenant_id = NULL` (incluso para configs específicas de tenant)

**Casos de uso:**
- Cambiar límite global de QRs de 7 a 14 días
- Desactivar feature flag en producción
- Configurar rate limits por tenant group

### 3.3 Dominio de Billing/Monetización (DSNO-BILLING)

**Propósito:** Asignar y gestionar planes comerciales por tenant.

**Tabla de relación:**
```sql
CREATE TABLE tenant_billing_plans (
    assignment_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    plan_type VARCHAR(32) NOT NULL,  -- FREE | PRO | ENTERPRISE
    billing_cycle VARCHAR(16) NOT NULL,  -- MONTHLY | ANNUAL
    assigned_by_identity_id VARCHAR(64) NOT NULL,
    assigned_at TIMESTAMP NOT NULL,
    effective_from TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NULL,
    auto_renew BOOLEAN NOT NULL DEFAULT true,
    cancelled BOOLEAN NOT NULL DEFAULT false,
    cancelled_by_identity_id VARCHAR(64) NULL,
    cancelled_at TIMESTAMP NULL
);
```

**Authority requerida:** `BILLING_ADMIN` (nueva)

**Acciones:**
- `assign_billing_plan()` - Asignar plan a tenant
- `upgrade_billing_plan()` - Upgrade de plan
- `cancel_billing_plan()` - Cancelar plan
- `list_tenant_plans()` - Listar planes por tenant

**Eventos:**
- `entidad = "BILLING_PLAN_ASSIGNMENT"`
- `tenant_id = NULL`

**Casos de uso:**
- Upgrade de tenant de Free a Pro
- Cancelar plan por falta de pago
- Listar tenants en trial que expiran pronto

### 3.4 Dominio de Feature Flags (DSNO-FEATURES)

**Propósito:** Habilitar/deshabilitar features por tenant sin redeploy.

**Tabla de relación:**
```sql
CREATE TABLE tenant_feature_flags (
    flag_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    feature_key VARCHAR(128) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    enabled_by_identity_id VARCHAR(64) NOT NULL,
    enabled_at TIMESTAMP NOT NULL,
    disabled_by_identity_id VARCHAR(64) NULL,
    disabled_at TIMESTAMP NULL,
    metadata JSON NULL  -- A/B test group, rollout percentage, etc.
);
```

**Authority requerida:** `FEATURE_ADMIN` (nueva)

**Acciones:**
- `enable_feature()` - Activar feature para tenant
- `disable_feature()` - Desactivar feature
- `list_tenant_features()` - Listar features activas
- `rollout_feature()` - Rollout gradual (10%, 50%, 100%)

**Eventos:**
- `entidad = "FEATURE_FLAG"`
- `tenant_id = NULL`

**Casos de uso:**
- Activar "facial_recognition" solo para tenants Pro
- Desactivar feature con bugs en producción
- A/B testing de nueva UI en 20% de tenants

### 3.5 Dominio de Integrations (DSNO-INTEGRATIONS)

**Propósito:** Gestionar integraciones externas por tenant.

**Tabla de relación:**
```sql
CREATE TABLE tenant_integrations (
    integration_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    integration_type VARCHAR(32) NOT NULL,  -- WEBHOOK | API | SSO
    integration_config JSON NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    configured_by_identity_id VARCHAR(64) NOT NULL,
    configured_at TIMESTAMP NOT NULL,
    last_success_at TIMESTAMP NULL,
    last_failure_at TIMESTAMP NULL,
    failure_count INTEGER DEFAULT 0,
    disabled_by_identity_id VARCHAR(64) NULL,
    disabled_at TIMESTAMP NULL
);
```

**Authority requerida:** `INTEGRATION_ADMIN` (nueva)

**Acciones:**
- `configure_integration()` - Configurar integración
- `test_integration()` - Probar conectividad
- `disable_integration()` - Deshabilitar integración
- `list_integrations()` - Listar integraciones por tenant

**Eventos:**
- `entidad = "TENANT_INTEGRATION"`
- `tenant_id = NULL`

---

## 4. Patrón de Implementación Multidominio

### 4.1 Estructura de Directorios Propuesta

```
backend/
  core/
    meta/          # Dominio Meta-Operativo (EXISTENTE)
      __init__.py
      validators.py
      assignments.py
      events.py
    
    audit/         # Dominio de Auditoría (NUEVO)
      __init__.py
      validators.py
      delegations.py
      events.py
    
    config/        # Dominio de Configuración (NUEVO)
      __init__.py
      validators.py
      configurations.py
      events.py
    
    billing/       # Dominio de Billing (NUEVO)
      __init__.py
      validators.py
      plans.py
      events.py
    
    features/      # Dominio de Features (NUEVO)
      __init__.py
      validators.py
      flags.py
      events.py
    
    integrations/  # Dominio de Integrations (NUEVO)
      __init__.py
      validators.py
      connectors.py
      events.py
    
    dsno_base/     # Base abstracta compartida (NUEVO)
      __init__.py
      validators.py
      events.py
      models.py
```

### 4.2 Clase Base Abstracta

```python
# backend/core/dsno_base/base.py

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from backend.db.models import Usuario

class DominioSeparadoNoOperativo(ABC):
    """
    Clase base abstracta para todos los Dominios Separados No Operativos.
    
    Responsabilidades:
      - Definir interfaz común para dominios separados
      - Garantizar que tenant_id = NULL en eventos
      - Validar authority específica del dominio
      - Registrar trazabilidad
    
    Invariantes:
      1. NO opera dentro de tenant
      2. NO accede a datos operativos
      3. Requiere authority específica
      4. Genera eventos con tenant_id = NULL
    """
    
    @property
    @abstractmethod
    def DOMAIN_NAME(self) -> str:
        """Nombre del dominio (ej: 'META', 'AUDIT', 'CONFIG')."""
        pass
    
    @property
    @abstractmethod
    def REQUIRED_AUTHORITY_TYPE(self) -> str:
        """Authority requerida para este dominio."""
        pass
    
    @property
    @abstractmethod
    def EVENT_ENTITY(self) -> str:
        """Nombre de entidad para eventos."""
        pass
    
    def validate_authority(self, db: Session, actor_identity_id: str) -> None:
        """
        Valida que el actor tenga authority requerida.
        Implementación común con authority_type parametrizable.
        """
        from backend.db.models import Authority, GovStatus
        
        authority = db.query(Authority).filter(
            Authority.identity_id == actor_identity_id,
            Authority.tipo == self.REQUIRED_AUTHORITY_TYPE,
            Authority.estado == GovStatus.ACTIVO
        ).first()
        
        if not authority:
            raise HTTPException(
                status_code=403,
                detail=f"No tiene authority {self.REQUIRED_AUTHORITY_TYPE} para dominio {self.DOMAIN_NAME}"
            )
    
    def registrar_evento(
        self,
        db: Session,
        actor: Usuario,
        session_token: str,
        entity_id: str,
        action: str,
        resultado: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra evento del dominio separado.
        GARANTIZA tenant_id = NULL.
        """
        from backend.core.event.registry import registrar_evento as registrar_evento_aup
        
        registrar_evento_aup(
            db=db,
            identity=actor,
            session_token=session_token,
            tenant_id=None,  # ← CRÍTICO: NULL para dominios separados
            entidad=self.EVENT_ENTITY,
            entidad_id=entity_id,
            accion=action,
            resultado=resultado,
            metadata=metadata or {}
        )
    
    @abstractmethod
    def create(self, db: Session, actor: Usuario, params: Dict[str, Any]) -> Any:
        """Crear relación/configuración."""
        pass
    
    @abstractmethod
    def revoke(self, db: Session, actor: Usuario, entity_id: str) -> Any:
        """Revocar relación/configuración."""
        pass
    
    @abstractmethod
    def list(self, db: Session, actor: Usuario, filters: Dict[str, Any]) -> list:
        """Listar relaciones/configuraciones."""
        pass
```

### 4.3 Ejemplo de Implementación: Dominio de Auditoría

```python
# backend/core/audit/delegations.py

from backend.core.dsno_base.base import DominioSeparadoNoOperativo
from backend.db.models import AuditDelegation  # Nuevo modelo

class DominioAuditoria(DominioSeparadoNoOperativo):
    """
    Dominio Separado No Operativo: Auditoría.
    
    Gestiona delegaciones temporales de capacidad de auditoría.
    """
    
    DOMAIN_NAME = "AUDIT"
    REQUIRED_AUTHORITY_TYPE = "AUDIT_ADMIN"
    EVENT_ENTITY = "AUDIT_DELEGATION"
    
    def create(self, db: Session, actor: Usuario, params: Dict[str, Any]) -> AuditDelegation:
        """
        Delegar acceso de auditoría temporal.
        
        Precondiciones:
          1. actor tiene authority AUDIT_ADMIN
          2. auditor_identity existe
          3. target_tenant existe
          4. expires_at es futuro
        """
        # 1. Validar authority
        self.validate_authority(db, actor.usuario_id)
        
        # 2. Validar entidades (similar a meta)
        validate_identity_exists(db, params['auditor_identity_id'])
        validate_tenant_exists(db, params['target_tenant_id'])
        
        # 3. Validar temporalidad
        if params['expires_at'] <= datetime.utcnow():
            raise HTTPException(400, "expires_at debe ser futuro")
        
        # 4. Crear delegación
        delegation = AuditDelegation(
            delegation_id=f"audit_{uuid.uuid4().hex[:16]}",
            auditor_identity_id=params['auditor_identity_id'],
            target_tenant_id=params['target_tenant_id'],
            audit_scope=params['audit_scope'],
            delegated_by_identity_id=actor.usuario_id,
            delegated_at=datetime.utcnow(),
            expires_at=params['expires_at']
        )
        
        db.add(delegation)
        db.commit()
        
        # 5. Evento (tenant_id=NULL garantizado por clase base)
        self.registrar_evento(
            db=db,
            actor=actor,
            session_token=params['session_token'],
            entity_id=delegation.delegation_id,
            action="DELEGATE",
            resultado="PERMITIDO",
            metadata={
                "auditor_identity_id": params['auditor_identity_id'],
                "target_tenant_id": params['target_tenant_id'],
                "audit_scope": params['audit_scope']
            }
        )
        
        return delegation
    
    def revoke(self, db: Session, actor: Usuario, entity_id: str) -> AuditDelegation:
        """Revocar delegación de auditoría."""
        # Similar a revoke_identity_from_tenant()
        pass
    
    def list(self, db: Session, actor: Usuario, filters: Dict[str, Any]) -> list:
        """Listar delegaciones activas."""
        # Similar a list_tenant_assignments()
        pass
```

---

## 5. Autoridades Multidominio

### 5.1 Jerarquía de Authorities Propuesta

```
AuthorityType (enum extendido):
  - GLOBAL              (existente) → Meta-operativo
  - FIRST_TIER          (existente) → Administrador de tenant
  
  - AUDIT_ADMIN         (nuevo)     → Auditoría multidominio
  - CONFIG_ADMIN        (nuevo)     → Configuración global
  - BILLING_ADMIN       (nuevo)     → Billing y monetización
  - FEATURE_ADMIN       (nuevo)     → Feature flags
  - INTEGRATION_ADMIN   (nuevo)     → Integraciones
```

### 5.2 Separación de Concerns

```
┌─────────────────────────────────────────────────────────────┐
│  DOMINIO OPERATIVO (dentro de tenant)                       │
│  • Visitas, QRs, Evidencias                                 │
│  • Requiere: SCOPE activo                                   │
│  • tenant_id = PRESENTE                                     │
│  • Middleware: RequireTenant                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  DOMINIOS SEPARADOS NO OPERATIVOS (sin tenant)              │
│                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ META-OPERATIVO│  │   AUDITORÍA   │  │ CONFIGURACIÓN │   │
│  │ GLOBAL auth   │  │ AUDIT_ADMIN   │  │ CONFIG_ADMIN  │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │    BILLING    │  │   FEATURES    │  │ INTEGRATIONS  │   │
│  │ BILLING_ADMIN │  │ FEATURE_ADMIN │  │INTEGRATION_ADM│   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                                                              │
│  • NO tienen tenant_id activo                               │
│  • tenant_id = NULL en eventos                              │
│  • Middleware: RequireSpecificAuthority                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Migración y Compatibilidad

### 6.1 Sin Impacto en Dominio Operativo

```
✅ El dominio operativo NO se modifica
✅ Los endpoints existentes NO cambian
✅ RLS permanece intacto
✅ Validaciones de scope NO se tocan
```

### 6.2 Adición Incremental

Cada nuevo dominio separado:
1. Se agrega de forma independiente
2. NO afecta dominios existentes
3. Tiene su propia tabla de relaciones
4. Tiene su propia authority
5. Tiene sus propios eventos (tenant_id=NULL)

### 6.3 Ejemplo de Roadmap

```
Fase actual:
  ✅ Dominio Meta-Operativo v1.0 (CONGELADO)

Fase 2 (opcional, si se requiere):
  ⬜ Dominio de Auditoría v1.0
  
Fase 3:
  ⬜ Dominio de Feature Flags v1.0
  
Fase 4:
  ⬜ Dominio de Billing v1.0
  
Fase 5:
  ⬜ Dominio de Configuración v1.0
```

Cada fase es independiente y opcional.

---

## 7. Beneficios de la Abstracción Multidominio

### 7.1 Arquitectónicos

```
✅ Separación de concerns clara
✅ Cada dominio es pequeño y cerrado
✅ Facilita testing independiente
✅ Reduce acoplamiento
✅ Permite deployment independiente
```

### 7.2 Operacionales

```
✅ Auditoría granular por dominio
✅ Authority específica reduce riesgos
✅ tenant_id=NULL garantiza separación
✅ Fácil identificar eventos de gobierno vs operativos
```

### 7.3 De Negocio

```
✅ Habilita monetización (billing)
✅ Permite rollout controlado (features)
✅ Facilita compliance (audit)
✅ Reduce time-to-market de nuevas capacidades
```

---

## 8. Restricciones y Límites

### 8.1 Restricción: Un Dominio = Un Propósito

Cada dominio separado debe tener UN propósito específico y cerrado.

NO hacer:
```
❌ DominioDeTodo: gestiona assignments, billing, features, audit
```

SÍ hacer:
```
✅ DominioMeta: solo assignments Identity→Tenant
✅ DominioBilling: solo planes comerciales
✅ DominioAudit: solo delegaciones de auditoría
```

### 8.2 Restricción: Dominios No Se Comunican

Dominios separados NO se llaman entre sí directamente.

NO hacer:
```
❌ DominioBilling.assign_plan() → DominioMeta.assign_identity()
```

SÍ hacer:
```
✅ Cada dominio es independiente
✅ Si hay dependencia, resolver en capa de aplicación
```

### 8.3 Restricción: tenant_id=NULL Es Inmutable

TODOS los eventos de dominios separados DEBEN tener `tenant_id=NULL`.

Esto permite:
- Filtrar eventos operativos vs gobierno
- Auditoría clara de acciones cross-tenant
- Separación forense

---

## 9. Conclusión

### 9.1 Patrón Descubierto

El Dominio Meta-Operativo v1.0 revela un **patrón arquitectónico reutilizable**:

> "Dominio Separado No Operativo: Una capa que gestiona configuraciones/relaciones 
> que habilitan operaciones, sin ejecutar lógica de negocio ni operar dentro de tenant."

### 9.2 Capacidad Multidominio

El sistema MSP_AXS tiene capacidad de **crecer horizontalmente** agregando dominios separados:

- ✅ **Implementado:** Meta-Operativo (assignments Identity→Tenant)
- 🔮 **Posible:** Auditoría, Config, Billing, Features, Integrations
- ⚠️ **Cada uno:** Independiente, cerrado, con su propia authority

### 9.3 Sin Romper Congelamiento

La abstracción NO viola el congelamiento del dominio meta v1.0:

- El dominio meta permanece CERRADO
- Nuevos dominios son INDEPENDIENTES
- Siguen el mismo PATRÓN
- NO modifican lógica existente

### 9.4 Valor Estratégico

Esta abstracción permite:

```
Sistema actual:
  Dominio Operativo + Dominio Meta

Sistema futuro (sin rediseño):
  Dominio Operativo
    + Dominio Meta (congelado)
    + Dominio Audit
    + Dominio Config
    + Dominio Billing
    + Dominio Features
    + ...
```

Cada dominio separado:
- Se agrega sin afectar otros
- Tiene su propia autorización
- Genera su propia auditoría
- Es pequeño, cerrado y defendible

---

**Estado:** Análisis de abstracción completado  
**Próxima decisión:** ¿Implementar otros dominios separados?  
**Recomendación:** Esperar demanda funcional antes de agregar dominios

---

**Autor:** Análisis arquitectónico basado en implementación real  
**Fecha:** 1 de enero de 2026
