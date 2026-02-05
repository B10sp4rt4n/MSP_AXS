# ESPECIFICACIÓN TÉCNICA: Campo `usuarios.rol`

**Sistema:** MSP_AXS  
**Versión:** 1.0.0  
**Fecha:** 2026-01-01  
**Clasificación:** Definición Estructural Obligatoria

---

## 1. DEFINICIÓN FORMAL

### 1.1 Qué ES `usuarios.rol`

| Propiedad | Valor |
|-----------|-------|
| **Tipo** | Metadata descriptiva de identidad |
| **Naturaleza** | Etiqueta estática de clasificación |
| **Propósito** | Identificar el perfil funcional del usuario para contextos NO operativos |
| **Alcance** | Solo UI, reportes, filtros visuales, comunicación humana |
| **Fuente de verdad** | NO |
| **Mutabilidad** | Sí (sin impacto operativo) |

**Definición formal:**
```
usuarios.rol ∈ {metadata_descriptiva}
usuarios.rol ∉ {fuente_de_poder, fuente_de_alcance, fuente_de_límite}
```

### 1.2 Qué NO ES `usuarios.rol`

| `rol` NO ES | Explicación |
|-------------|-------------|
| Permiso | No otorga capacidad de ejecutar acciones |
| Autoridad | No declara poder de gobierno |
| Alcance | No define dónde puede operar |
| Política | No establece límites |
| Access control | No participa en decisiones de autorización |
| Token claim | No se serializa en JWT para validación |

### 1.3 Usos PERMITIDOS

| Uso | Ejemplo |
|-----|---------|
| Mostrar en UI | "Bienvenido, Juan (Administrador)" |
| Filtrar reportes | "Mostrar solo usuarios con rol GUARDIA" |
| Comunicación | "El rol del usuario es RESIDENTE" |
| Onboarding | "Asignar plantilla de inicio según rol" |
| Segmentación visual | "Dashboard diferente por rol" |

### 1.4 Usos PROHIBIDOS

| Uso PROHIBIDO | Por qué es violación |
|---------------|----------------------|
| `if rol == 'MSP_ADMIN': crear_tenant()` | Poder proviene de `authorities_gov`, no de `rol` |
| `if rol == 'GUARDIA': validar_qr()` | Capacidad proviene de `user_tenant_scope`, no de `rol` |
| `if rol in ['ADMIN', 'MSP_ADMIN']: bypass_policy()` | Límites provienen de `policies_gov`, no de `rol` |
| `jwt.claims['rol'] = usuario.rol` | `rol` no participa en autenticación/autorización |
| `query.filter(rol='ADMIN').allow_all()` | Decisiones de acceso no dependen de `rol` |

---

## 2. CONVENCIÓN DE NOMBRES

### 2.1 Análisis de opciones

| Opción | Ventajas | Desventajas | Veredicto |
|--------|----------|-------------|-----------|
| Mantener `rol` | Compatibilidad total, sin migración | Nombre sugiere poder | ❌ No recomendado |
| Renombrar a `perfil_ui` | Claridad semántica | Requiere migración | ⚠️ Parcial |
| Renombrar a `tipo_identidad` | Neutral, descriptivo | Sigue sonando clasificatorio | ⚠️ Aceptable |
| Renombrar a `etiqueta_usuario` | Explícitamente metadata | Verbose | ⚠️ Parcial |
| Renombrar a `identity_label` | Claramente etiqueta, no rol | Inglés en modelo español | ✅ Recomendado |
| Renombrar a `identity_tag` | Semánticamente débil (mejor) | Inglés en modelo español | ✅ Alternativa |
| Renombrar a `ui_profile` | Ultra claro: solo presentación | Inglés en modelo español | ⚠️ Parcial |

### 2.2 Recomendación: Renombrar a `identity_label`

**Justificación:**
- "Label" es explícitamente una etiqueta (no categoría fuerte)
- Semánticamente débil → menor riesgo de abuso en ML, reglas o automatización
- "Identity" conecta con AUP_IDENTITY
- Compatible con valores actuales (`MSP_ADMIN`, `GUARDIA`, `RESIDENTE`)

**Nota:** `tipo_identidad` es aceptable si se prefiere consistencia en español.
La diferencia es fine-tuning semántico, no urgencia.

### 2.3 Migración sin ruptura

**Fase 1: Alias (inmediato)**
```sql
-- Crear vista de compatibilidad
CREATE VIEW usuarios_compat AS 
SELECT *, rol AS identity_label FROM usuarios;

-- Comentario obligatorio en columna original
COMMENT ON COLUMN usuarios.rol IS 
'DEPRECATED: Usar identity_label. Este campo es SOLO metadata descriptiva. 
NO otorga permisos, poder ni alcance. Poder proviene EXCLUSIVAMENTE de 
authorities_gov + user_tenant_scope + policies_gov.';

-- Comentario en vista con fecha de muerte
COMMENT ON VIEW usuarios_compat IS
'⚠️ VISTA DE COMPATIBILIDAD TEMPORAL
Fecha de muerte: 2026-04-01 (90 días desde creación)
NO usar en lógica nueva. Será eliminada.
Migrar a tabla usuarios con columna identity_label.';
```

**Fase 2: Renombrar (cuando sea seguro)**
```sql
ALTER TABLE usuarios RENAME COLUMN rol TO identity_label;
```

**Fase 3: Eliminar alias**
```sql
DROP VIEW usuarios_compat;
```

### 2.4 Alternativa: Mantener `rol` con guardrails

Si migración no es viable, mantener `rol` con:
1. Comentario explícito en DB
2. Documentación obligatoria
3. Linter de código que detecte usos prohibidos

---

## 3. REGLAS TÉCNICAS OBLIGATORIAS

### 3.1 Invariantes del Sistema

```
INVARIANTE-ROL-001:
  Si código evalúa `usuarios.rol` para decidir permiso → BUG CRÍTICO
  
INVARIANTE-ROL-002:
  Si código evalúa `usuarios.rol` para decidir alcance → BUG CRÍTICO
  
INVARIANTE-ROL-003:
  Si código evalúa `usuarios.rol` para decidir límites → BUG CRÍTICO
  
INVARIANTE-ROL-004:
  Si JWT contiene claim derivado de `usuarios.rol` para autorización → BUG CRÍTICO
  
INVARIANTE-ROL-005:
  Si query filtra por `rol` para otorgar acceso a recurso → BUG CRÍTICO
```

### 3.2 Matriz de Decisión de Autorización

| Pregunta | Campo correcto | Campo INCORRECTO |
|----------|----------------|------------------|
| ¿Puede crear tenants? | `authorities_gov.tipo` | ~~`usuarios.rol`~~ |
| ¿Puede operar en tenant X? | `user_tenant_scope.tenant_id` | ~~`usuarios.rol`~~ |
| ¿Puede generar QR de 30 días? | `policies_gov.limites` | ~~`usuarios.rol`~~ |
| ¿Tiene autoridad global? | `authorities_gov.tipo = 'global'` | ~~`usuarios.rol = 'MSP_ADMIN'`~~ |
| ¿Es guardia en condo A? | `user_tenant_scope.access_level = 'guardia'` | ~~`usuarios.rol = 'GUARDIA'`~~ |

### 3.3 Código de Ejemplo: Correcto vs Incorrecto

**❌ INCORRECTO (Bug crítico):**
```python
def puede_crear_tenant(usuario):
    return usuario.rol == 'MSP_ADMIN'  # VIOLACIÓN: rol no otorga poder
```

**✅ CORRECTO:**
```python
def puede_crear_tenant(usuario_id: str, db_gov: Session) -> bool:
    authority = db_gov.query(Authority).filter(
        Authority.identity_id == usuario_id,
        Authority.tipo == AuthorityType.GLOBAL,
        Authority.estado == GovStatus.ACTIVO
    ).first()
    return authority is not None
```

**❌ INCORRECTO (Bug crítico):**
```python
def puede_validar_qr(usuario, tenant_id):
    return usuario.rol in ['GUARDIA', 'ADMIN_CONDOMINIO']  # VIOLACIÓN
```

**✅ CORRECTO:**
```python
def puede_validar_qr(usuario_id: str, tenant_id: str, db_core: Session) -> bool:
    scope = db_core.query(UserTenantScope).filter(
        UserTenantScope.usuario_id == usuario_id,
        UserTenantScope.tenant_id == tenant_id,
        UserTenantScope.estado == ScopeStatus.ACTIVO,
        UserTenantScope.access_level.in_([AccessLevel.GUARDIA, AccessLevel.ADMIN_CONDOMINIO])
    ).first()
    return scope is not None
```

---

## 4. GUARDRAILS TÉCNICOS

### 4.1 Comentario obligatorio en base de datos

```sql
COMMENT ON COLUMN usuarios.rol IS 
'╔═══════════════════════════════════════════════════════════════════════════╗
 ║ ⚠️  METADATA DESCRIPTIVA - NO OTORGA PODER                                ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║ Este campo es EXCLUSIVAMENTE para:                                        ║
 ║   - UI (mostrar perfil)                                                   ║
 ║   - Reportes (filtrar por tipo)                                           ║
 ║   - Comunicación humana                                                   ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║ PROHIBIDO usar para:                                                      ║
 ║   - Decisiones de autorización                                            ║
 ║   - Validación de permisos                                                ║
 ║   - Filtros de acceso a recursos                                          ║
 ╠═══════════════════════════════════════════════════════════════════════════╣
 ║ FUENTES DE PODER:                                                         ║
 ║   - authorities_gov → QUÉ puede gobernar                                  ║
 ║   - user_tenant_scope → DÓNDE puede operar                                ║
 ║   - policies_gov → BAJO QUÉ LÍMITES                                       ║
 ╚═══════════════════════════════════════════════════════════════════════════╝';
```

### 4.2 Linter de código (regla para CI/CD)

**Patrón 1: Detección específica (contexto de autorización)**
```regex
# Detectar usos sospechosos de rol en decisiones
\.(rol|role)\s*[=!]=\s*['"][A-Z_]+['"].*(?:return|if|allow|permit|grant|can_)
```

**Patrón 2: Detección burda (preferir falsos positivos)**
```regex
# Detectar CUALQUIER comparación con rol
rol\s*==
```

**Regla de CI:**
```yaml
# .github/workflows/lint-aup.yml
- name: Detectar uso incorrecto de rol (específico)
  run: |
    if grep -rn "\.rol\s*==" backend/ --include="*.py" | grep -v "# UI-ONLY"; then
      echo "ERROR: Uso de rol en lógica de negocio detectado"
      exit 1
    fi

- name: Detectar uso incorrecto de rol (burdo)
  run: |
    # Más agresivo: detecta cualquier comparación con rol
    # Prefiere falsos positivos a falsos negativos
    MATCHES=$(grep -rn "rol\s*==" backend/ --include="*.py" | grep -v "# METADATA-SAFE" || true)
    if [ -n "$MATCHES" ]; then
      echo "⚠️ ADVERTENCIA: Posible uso de rol en lógica detectado:"
      echo "$MATCHES"
      echo ""
      echo "Si es uso legítimo (UI/reportes), agregar comentario: # METADATA-SAFE"
      exit 1
    fi
```

### 4.3 Docstring obligatorio en modelo

```python
class Usuario(Base_CORE):
    """
    AUP_IDENTITY: Entidad que puede autenticarse.
    
    ⚠️ CAMPO `rol`:
      - ES: Metadata descriptiva (UI, reportes)
      - NO ES: Fuente de permisos, poder o alcance
      - PODER PROVIENE DE: authorities_gov, user_tenant_scope, policies_gov
    """
    __tablename__ = "usuarios"
    
    # ... campos ...
    
    rol = Column(String)  # ⚠️ METADATA ONLY - Ver docstring
```

### 4.4 Test de regresión obligatorio

```python
# tests/test_aup_invariants.py

def test_rol_no_otorga_poder():
    """
    INVARIANTE: El campo rol NO debe usarse en decisiones de autorización.
    
    Si este test falla, existe código que viola principios AUP.
    """
    import ast
    import os
    
    violations = []
    
    for root, dirs, files in os.walk('backend'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath) as f:
                    tree = ast.parse(f.read())
                    
                for node in ast.walk(tree):
                    # Detectar comparaciones con .rol
                    if isinstance(node, ast.Compare):
                        if hasattr(node.left, 'attr') and node.left.attr == 'rol':
                            # Verificar si está en contexto de autorización
                            # (heurística: función que retorna bool o tiene 'puede', 'can', 'allow')
                            violations.append(f"{filepath}: uso de .rol en comparación")
    
    assert len(violations) == 0, f"Violaciones de INVARIANTE-ROL detectadas:\n" + "\n".join(violations)
```

---

## 5. RESUMEN EJECUTIVO

| Aspecto | Decisión |
|---------|----------|
| **Definición** | `rol` = metadata descriptiva, NO fuente de poder |
| **Renombrar** | Recomendado: `identity_label` (migración en fases, vista con fecha de muerte) |
| **Guardrails** | Comentario DB + linter CI (2 reglas) + test regresión + docstring |
| **Invariantes** | 5 reglas explícitas (violación = bug crítico) |

**Resultado esperado:**
- Ambigüedad semántica eliminada
- Desarrolladores sin duda sobre uso correcto
- CI/CD detecta violaciones automáticamente
- Modelo AUP intacto

---

## APÉNDICE: Checklist de Implementación

- [ ] Agregar COMMENT ON COLUMN en base de datos
- [ ] Actualizar docstring en modelo `Usuario`
- [ ] Agregar regla de linter específica en CI/CD
- [ ] Agregar regla de linter burda en CI/CD
- [ ] Crear test `test_rol_no_otorga_poder`
- [ ] (Fase 1) Crear vista `usuarios_compat` con comentario y fecha de muerte
- [ ] (Fase 2) Renombrar columna a `identity_label`
- [ ] (Fase 3) Eliminar vista `usuarios_compat` en 2026-04-01
- [ ] Actualizar bootstrap SQL con comentario
- [ ] Documentar en onboarding de desarrolladores

---

**FIN DE ESPECIFICACIÓN**
