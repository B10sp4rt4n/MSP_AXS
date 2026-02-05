# Issue #0: Testing Infrastructure & CI/CD
## Resolver Deuda Técnica Crítica antes de MVP

**Prioridad:** 🟡 P1 - ALTA (Pre-requisito para escalabilidad)  
**Estimación:** 5-7 días  
**Objetivo:** Subir test coverage de 3.5% a 60%+  
**Fecha inicio:** 5 Febrero 2026  
**Fecha fin:** 12 Febrero 2026

---

## 🎯 JUSTIFICACIÓN

### Estado Actual
```
Líneas de código backend:   10,987
Líneas de tests:              389
Coverage actual:             3.5%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Coverage industria SaaS:      70-80%
Brecha:                       -66.5%
```

### Riesgos sin Testing
- ❌ **Refactoring imposible** - Cualquier cambio puede romper producción
- ❌ **Escalabilidad bloqueada** - No podemos agregar features con confianza
- ❌ **Due diligence fallará** - Inversionistas técnicos rechazan
- ❌ **Debugging lento** - Sin tests, cada bug toma horas
- ❌ **Onboarding difícil** - Nuevos devs tienen miedo de romper cosas

### Beneficios con Testing
- ✅ **Confidence para refactorizar** - Tests verifican que nada se rompió
- ✅ **Documentación viva** - Tests muestran cómo usar cada función
- ✅ **Faster debugging** - Tests aíslan el problema en minutos
- ✅ **CI/CD habilitado** - Deploy automático con verificación
- ✅ **Due diligence pass** - Demuestra madurez técnica

---

## 📋 PLAN DE EJECUCIÓN

### Día 1: Setup & AUP_SESSION (5 Feb)
**Target:** 15% coverage

- [ ] **Configuración base**
  - [ ] Instalar `pytest-cov`, `pytest-asyncio`, `httpx`
  - [ ] Configurar `pytest.ini` con flags
  - [ ] Crear `conftest.py` con fixtures compartidas
  - [ ] GitHub Actions workflow básico

- [ ] **Tests AUP_SESSION** (crítico - bloquea todas las requests)
  ```
  tests/test_aup_session/
  ├── test_jwt.py          # create_access_token, decode_access_token
  ├── test_password.py     # hash, verify
  ├── test_middleware.py   # AUPSessionGuard
  └── test_dependencies.py # get_current_user
  ```
  - [ ] `test_jwt_create_access_token_valido`
  - [ ] `test_jwt_token_expirado_falla`
  - [ ] `test_jwt_token_invalido_falla`
  - [ ] `test_password_hash_verify_ok`
  - [ ] `test_middleware_sin_token_bloquea_401`
  - [ ] `test_middleware_token_valido_pasa`
  - [ ] `test_get_current_user_desde_token`

### Día 2: AUP_SCOPE (6 Feb)
**Target:** 30% coverage

- [ ] **Tests AUP_SCOPE** (multi-tenancy crítico)
  ```
  tests/test_aup_scope/
  ├── test_tenant_validation.py  # Validar tenant_id en scope
  ├── test_role_hierarchy.py     # SUPER_ADMIN > MSP_ADMIN > ADMIN
  └── test_scope_enforcement.py  # Usuarios solo ven su tenant
  ```
  - [ ] `test_usuario_solo_ve_su_tenant`
  - [ ] `test_super_admin_ve_todos_los_tenants`
  - [ ] `test_admin_no_puede_crear_msp`
  - [ ] `test_scope_invalido_retorna_403`

### Día 3: AUP_EVENT (7 Feb)
**Target:** 45% coverage

- [ ] **Tests AUP_EVENT** (trazabilidad crítica)
  ```
  tests/test_aup_event/
  ├── test_registry.py       # registrar_evento
  ├── test_hash.py           # calcular_hash_evento
  └── test_immutability.py   # Eventos no se pueden modificar
  ```
  - [ ] `test_registrar_evento_crea_hash_correcto`
  - [ ] `test_hash_evento_es_determinista`
  - [ ] `test_evento_guardado_tiene_todos_los_campos`
  - [ ] `test_modificar_evento_rompe_hash` (verificar inmutabilidad)

### Día 4: AUP_GOV (8 Feb)
**Target:** 60% coverage

- [ ] **Tests AUP_GOV** (políticas comerciales)
  ```
  tests/test_aup_gov/
  ├── test_policy.py          # CRUD políticas
  ├── test_delegation.py      # Delegaciones temporales
  ├── test_plans.py           # FREE, PRO, ENTERPRISE
  └── test_integration.py     # Policy → Event flow completo
  ```
  - [ ] `test_crear_policy_global`
  - [ ] `test_crear_policy_tenant_especifico`
  - [ ] `test_evaluar_policy_cumple_limites`
  - [ ] `test_evaluar_policy_excede_limite_falla`
  - [ ] `test_delegar_autoridad_temporal_valida`
  - [ ] `test_delegacion_expirada_falla`
  - [ ] `test_plan_free_limita_a_3_dias_qr`
  - [ ] `test_plan_pro_permite_7_dias_qr`

### Día 5: Integration Tests (9 Feb)
**Target:** 70% coverage

- [ ] **Tests de integración end-to-end**
  ```
  tests/test_integration/
  ├── test_flujo_login_completo.py
  ├── test_flujo_crear_visitante.py
  └── test_flujo_escaneo_qr.py (cuando exista)
  ```
  - [ ] `test_flujo_completo_login_jwt_get_user`
  - [ ] `test_flujo_residente_autoriza_visitante`
  - [ ] `test_flujo_guardia_sin_auth_bloqueado`

### Día 6: CI/CD Pipeline (10 Feb)

- [ ] **GitHub Actions workflow**
  ```yaml
  # .github/workflows/test.yml
  name: CI Tests
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            pip install -r requirements.txt
            pip install pytest pytest-cov pytest-asyncio httpx
        - name: Run tests
          run: |
            pytest --cov=backend --cov-report=term --cov-report=html
        - name: Coverage report
          run: |
            coverage report --fail-under=60
  ```

- [ ] **Pre-commit hooks**
  ```bash
  # .pre-commit-config.yaml
  repos:
    - repo: local
      hooks:
        - id: pytest
          name: pytest
          entry: pytest
          language: system
          pass_filenames: false
          always_run: true
  ```

### Día 7: Documentation & Cleanup (11-12 Feb)

- [ ] **README actualizado con badges**
  ```markdown
  ![Tests](https://github.com/B10sp4rt4n/MSP_AXS/workflows/CI%20Tests/badge.svg)
  ![Coverage](https://img.shields.io/badge/coverage-65%25-green)
  ```

- [ ] **Testing documentation**
  - [ ] `docs/TESTING_GUIDE.md` - Cómo correr tests
  - [ ] `docs/COVERAGE_REPORT.md` - Coverage por módulo

---

## 🎯 CRITERIOS DE ACEPTACIÓN

### Métricas de Éxito
- ✅ Coverage total backend: **≥60%**
- ✅ Coverage AUP_SESSION: **≥80%** (crítico)
- ✅ Coverage AUP_SCOPE: **≥70%**
- ✅ Coverage AUP_EVENT: **≥75%**
- ✅ Coverage AUP_GOV: **≥65%**
- ✅ GitHub Actions green ✓ en main
- ✅ Pre-commit hooks funcionando
- ✅ Coverage badge en README

### Tests que NO pueden fallar
```
tests/test_aup_session/test_middleware.py::test_middleware_sin_token_bloquea_401
tests/test_aup_event/test_hash.py::test_hash_evento_es_determinista
tests/test_aup_gov/test_policy.py::test_evaluar_policy_excede_limite_falla
```

---

## 📊 COVERAGE TARGET POR MÓDULO

| Módulo | Líneas | Coverage Actual | Target | Prioridad |
|--------|--------|-----------------|--------|-----------|
| `core/auth/` | ~500 | 5% | 80% | 🔴 Crítico |
| `core/aup_runtime_blocks.py` | ~400 | 0% | 85% | 🔴 Crítico |
| `core/event/` | ~350 | 10% | 75% | 🟡 Alta |
| `core/gov/` | ~800 | 0% | 65% | 🟡 Alta |
| `core/scope/` | ~300 | 0% | 70% | 🟡 Alta |
| `routers/` | ~1500 | 5% | 50% | 🟢 Media |
| `services/` | ~600 | 0% | 55% | 🟢 Media |
| `db/models/` | ~800 | 0% | 40% | 🟢 Baja |

---

## 🛠️ COMANDOS ÚTILES

### Instalar dependencias de testing
```bash
pip install pytest pytest-cov pytest-asyncio httpx faker
pip freeze > requirements.txt
```

### Correr tests con coverage
```bash
# Todos los tests
pytest --cov=backend --cov-report=term --cov-report=html

# Solo un módulo
pytest tests/test_aup_session/ --cov=backend.core.auth -v

# Ver reporte HTML
open htmlcov/index.html
```

### Ver líneas sin cubrir
```bash
pytest --cov=backend --cov-report=term-missing
```

### Correr solo tests rápidos
```bash
pytest -m "not slow" -v
```

---

## 📈 PROGRESO ESPERADO

```
Día 1: ████░░░░░░ 15%  (AUP_SESSION)
Día 2: ████████░░ 30%  (AUP_SCOPE)
Día 3: ████████████░░ 45%  (AUP_EVENT)
Día 4: ████████████████░░ 60%  (AUP_GOV)
Día 5: ████████████████████░ 70%  (Integration)
Día 6: ████████████████████░ 70%  (CI/CD setup)
Día 7: ████████████████████░ 70%  (Docs & cleanup)
```

---

## 🚀 IMPACTO EN INVESTOR PITCH

### Antes (Sin Testing)
```
"Tenemos arquitectura AUP única pero sin tests"
→ Riesgo percibido: ALTO
→ Valuación: $1.0M - $1.2M
```

### Después (Con Testing 60%+)
```
"Arquitectura AUP única + 60% test coverage + CI/CD"
→ Riesgo percibido: MEDIO
→ Valuación: $1.5M - $2.0M
→ "Production-ready, no solo un prototipo"
```

---

## ✅ CONCLUSIÓN

**Esta NO es una semana perdida, es una inversión que:**
- Desbloquea escalabilidad futura
- Reduce bugs en producción 10x
- Aumenta valuación $200K-$500K
- Demuestra madurez técnica a inversionistas
- Permite onboarding rápido de devs

**Tiempo total:** 5-7 días  
**ROI:** Infinito (sin tests, producto no puede escalar)

---

## 🔗 REFERENCIAS

- [BACKLOG_ISSUES.md](BACKLOG_ISSUES.md) - Backlog original
- [PLAN_30_DIAS.md](PLAN_30_DIAS.md) - Plan original (ahora modificado)
- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
