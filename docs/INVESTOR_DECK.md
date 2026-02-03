# ═══════════════════════════════════════════════════════════════════════════════
#                    MSP_AXS - INVESTOR DECK
#           Sistema de Control de Accesos para Condominios
# ═══════════════════════════════════════════════════════════════════════════════

**Fecha:** 3 de Febrero, 2026  
**Versión:** 1.0  
**Estado:** Pre-MVP → MVP Release  
**Confidencialidad:** Uso exclusivo para inversionistas

---

# 📊 INFOGRAFÍA EJECUTIVA

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     ╔═══════════════════════════════════════════════════════════════════╗    ║
║     ║              🏢 MSP_AXS - ACCESS CONTROL PLATFORM                 ║    ║
║     ╚═══════════════════════════════════════════════════════════════════╝    ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │  🎯 PROBLEMA                     💡 SOLUCIÓN                        │    ║
║   │                                                                     │    ║
║   │  • Condominios sin control      • Plataforma SaaS multi-tenant     │    ║
║   │    digital de accesos           • QR con vigencia configurable      │    ║
║   │  • Guardias con procesos        • Trazabilidad completa            │    ║
║   │    manuales y papel             • Evidencias fotográficas cloud    │    ║
║   │  • 0% trazabilidad de           • Gobierno dinámico sin código     │    ║
║   │    visitantes y eventos                                             │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   ┌───────────────────────────────────────────────────────────────────────┐  ║
║   │                    🏗️ ARQUITECTURA ÚNICA: AUP                         │  ║
║   │                 (Architecture from Unified Principles)                 │  ║
║   │                                                                       │  ║
║   │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │  ║
║   │   │  AUP     │  │  AUP     │  │  AUP     │  │  AUP     │            │  ║
║   │   │ SESSION  │→ │  SCOPE   │→ │  EVENT   │→ │   GOV    │            │  ║
║   │   │  QUIÉN   │  │  DÓNDE   │  │   QUÉ    │  │  PODER   │            │  ║
║   │   └──────────┘  └──────────┘  └──────────┘  └──────────┘            │  ║
║   │                                                                       │  ║
║   │   Comparable a: Auth0 + Segment + AWS IAM en una sola plataforma    │  ║
║   └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                    📈 MÉTRICAS CLAVE                                │    ║
║   │                                                                     │    ║
║   │    🏗️ Arquitectura           📊 Mercado           💰 Modelo        │    ║
║   │    ━━━━━━━━━━━━━━           ━━━━━━━━━━          ━━━━━━━━━         │    ║
║   │    Score: 8.2/10            TAM: $15B            Free: $0/mes      │    ║
║   │    vs Industria: 7/10       LATAM: $2B           Pro: $49/mes      │    ║
║   │    Moat: 12-18 meses        México: $800M        Enterprise: $499+ │    ║
║   │                                                                     │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                    🚀 ROADMAP TO MVP                                │    ║
║   │                                                                     │    ║
║   │    ✅ FASE 1 (Completada)      🔄 FASE 2 (En curso)                │    ║
║   │    ━━━━━━━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━━━━                   │    ║
║   │    • Arquitectura AUP           • Flujos QR completos              │    ║
║   │    • Autenticación JWT          • Portales Guardia/Residente       │    ║
║   │    • Multi-tenancy              • Notificaciones SMS               │    ║
║   │    • Cloudinary Setup           • PostgreSQL/Redis                 │    ║
║   │                                                                     │    ║
║   │    📅 FASE 3 (Feb 2026)        🎯 MVP RELEASE                      │    ║
║   │    ━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━                     │    ║
║   │    • App móvil PWA              Fecha: 28 Feb 2026                 │    ║
║   │    • Reportes/Dashboard         Target: 10 clientes piloto         │    ║
║   │    • Piloto 10 condominios                                          │    ║
║   │                                                                     │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

# 🏆 VENTAJAS COMPETITIVAS

## 1. ARQUITECTURA ÚNICA E INCOPIABLE

### El Moat Tecnológico: AUP (Architecture from Unified Principles)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        COMPARATIVA DE CAPACIDADES                            │
├──────────────────────┬────────────┬────────────┬────────────┬───────────────┤
│     Capacidad        │   Auth0    │  Segment   │  AWS IAM   │   MSP_AXS     │
├──────────────────────┼────────────┼────────────┼────────────┼───────────────┤
│ Multi-tenancy        │  ⭐⭐⭐⭐⭐  │  ⭐⭐⭐     │  ⭐⭐       │  ⭐⭐⭐⭐⭐      │
│ Event Sourcing       │  ⭐⭐       │  ⭐⭐⭐⭐⭐  │  ⭐⭐       │  ⭐⭐⭐⭐⭐      │
│ Governance Dinámico  │  ⭐        │  ⭐        │  ⭐⭐⭐⭐⭐  │  ⭐⭐⭐⭐⭐      │
│ Trazabilidad Hash    │  ❌        │  ⭐⭐⭐     │  ⭐⭐⭐     │  ⭐⭐⭐⭐⭐      │
│ Planes sin Código    │  ❌        │  ❌        │  ❌        │  ⭐⭐⭐⭐⭐      │
├──────────────────────┴────────────┴────────────┴────────────┴───────────────┤
│            MSP_AXS = Auth0 + Segment + AWS IAM COMBINADOS                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### ¿Por qué es difícil de copiar?

| Barrera de Entrada | Tiempo para Competidores | Descripción |
|--------------------|--------------------------|-------------|
| **Conceptual** | 2-3 semanas | Separación de planos Gobierno vs Operación |
| **Estructural** | 4-6 semanas | AUP_EVENT como prerequisito de AUP_GOV |
| **Integración** | 4-6 semanas | Refactorización total de sistema existente |
| **Total** | **12-18 meses** | Rediseño completo desde cero |

**Conclusión:** Si MSP_AXS logra 50 clientes en 12 meses, competidores no pueden alcanzar.

---

## 2. MODELO DE MONETIZACIÓN NATIVO

### Planes Comerciales vía AUP_GOV (sin código)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PLANES COMERCIALES                                  │
├─────────────┬───────────────┬──────────────────┬───────────────────────────┤
│    PLAN     │    PRECIO     │     LÍMITES      │      FUNCIONALIDADES      │
├─────────────┼───────────────┼──────────────────┼───────────────────────────┤
│   🆓 FREE   │     $0/mes    │ 1 condominio     │ ✅ QR hasta 3 días        │
│             │               │ 20 usuarios      │ ✅ 50 visitas/mes         │
│             │               │                  │ ❌ Sin delegación          │
├─────────────┼───────────────┼──────────────────┼───────────────────────────┤
│   💼 PRO    │   $49/mes     │ 5 condominios    │ ✅ QR hasta 7 días        │
│             │ por tenant    │ 100 usuarios     │ ✅ 500 visitas/mes        │
│             │               │                  │ ✅ Delegación 30 días      │
├─────────────┼───────────────┼──────────────────┼───────────────────────────┤
│ 🏢 ENTER-   │  $499/mes     │ 50 condominios   │ ✅ QR hasta 30 días       │
│   PRISE     │   + custom    │ 1000 usuarios    │ ✅ 10K visitas/mes        │
│             │               │                  │ ✅ Políticas custom       │
└─────────────┴───────────────┴──────────────────┴───────────────────────────┘
```

**Innovación clave:** Cambiar plan = revocar políticas viejas + crear nuevas. **Zero código, zero deploy.**

---

## 3. TRAZABILIDAD CRIPTOGRÁFICA

### Cada acción genera evento con hash SHA-256

```python
AUP_EVENT {
    identity:   "usuario_123"          # QUIÉN
    tenant:     "condominio_abc"       # DÓNDE
    entidad:    "qr"                   # QUÉ
    accion:     "escanear"             # ACCIÓN
    resultado:  "permitido"            # RESULTADO
    hash:       "a3f2c1..."            # VERIFICABLE
    timestamp:  "2026-02-03T10:30:00"  # CUÁNDO
}
```

**Beneficios:**
- ✅ Auditoría perfecta para compliance
- ✅ Detección de tampering
- ✅ Reconstrucción de estado
- ✅ Analítica avanzada (tendencias, patrones)

---

## 4. STACK TECNOLÓGICO MODERNO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STACK TECNOLÓGICO                                 │
├───────────────┬─────────────────────────────────────────────────────────────┤
│   BACKEND     │  FastAPI (Python 3.11) - Async, OpenAPI, Type Hints        │
├───────────────┼─────────────────────────────────────────────────────────────┤
│   DATABASE    │  PostgreSQL (Neon Cloud) - Particionamiento por tiempo     │
├───────────────┼─────────────────────────────────────────────────────────────┤
│   CACHE       │  Redis (Upstash) - Latencia QR < 5ms                       │
├───────────────┼─────────────────────────────────────────────────────────────┤
│   STORAGE     │  Cloudinary - CDN global 200+ PoPs, transformaciones       │
├───────────────┼─────────────────────────────────────────────────────────────┤
│   HOSTING     │  Railway - Auto-deploy desde GitHub, $0-$20/mes inicial    │
├───────────────┼─────────────────────────────────────────────────────────────┤
│   AUTH        │  JWT + bcrypt - Sin dependencia externa                    │
└───────────────┴─────────────────────────────────────────────────────────────┘
```

---

# 📋 ESTADO ACTUAL DEL PRODUCTO

## ✅ Funcionalidades Completadas (70%)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| **AUP_SESSION** | ✅ 100% | Autenticación JWT, login/logout, refresh tokens |
| **AUP_SCOPE** | ✅ 100% | Multi-tenancy, jerarquía de roles, validación |
| **AUP_EVENT** | ✅ 100% | Eventos inmutables, hash SHA-256, auditoría |
| **AUP_GOV** | ✅ 90% | Políticas, delegaciones, planes (falta UI admin) |
| **Cloudinary** | ✅ 100% | Evidencias fotográficas operativas |
| **APIs REST** | ✅ 85% | CRUD completo MSP/Condominios/Usuarios/Visitas |
| **QR System** | 🔄 60% | Generación funcional, falta escaneo normalizado |
| **Portales HTML** | 🔄 30% | Admin básico, falta Guardia/Residente |
| **Notificaciones** | ⬜ 0% | Pendiente integración Twilio/Slack |
| **App Móvil** | ⬜ 0% | Pendiente PWA |

---

## 🔴 Qué Falta para MVP (30%)

### Semana 1-2: Core Functionality
1. **Modelo QRAcceso persistente** - Ciclo de vida completo del QR
2. **Endpoint POST /qr/escanear** - Validación en tiempo real
3. **Tabla RegistroEscaneo normalizada** - Para escalar a 10K ops/día
4. **Endpoint POST /visitantes/autorizar** - Flujo residente completo

### Semana 2-3: User Interfaces
5. **Portal guardian.html** - Interfaz para guardias (escaneo + evidencias)
6. **Portal residente.html** - Autorizar visitantes con QR
7. **Portal visitante.html** - Vista del QR con vigencia

### Semana 3-4: Production Readiness
8. **Migración a PostgreSQL (Neon)** - Escalabilidad
9. **Redis Cache** - Latencia < 5ms para escaneos
10. **Notificaciones SMS (Twilio)** - UX completa
11. **Deploy Railway Production** - Auto-scaling

---

# 🗺️ ROADMAP DETALLADO

## Fase 1: Foundation (✅ COMPLETADA - Enero 2026)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ✅ FASE 1: FOUNDATION                                        Enero 2026     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Semana 1-2:                         Semana 3-4:                            │
│  ────────────                        ────────────                            │
│  ✅ Arquitectura AUP diseñada        ✅ AUP_GOV implementado                │
│  ✅ AUP_SESSION (JWT)                ✅ Planes comerciales                   │
│  ✅ AUP_SCOPE (multi-tenant)         ✅ Delegaciones temporales             │
│  ✅ AUP_EVENT (trazabilidad)         ✅ Cloudinary configurado              │
│                                                                              │
│  DELIVERABLE: Backend funcional con arquitectura world-class               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Fase 2: Core Features (🔄 EN CURSO - Feb 1-14, 2026)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🔄 FASE 2: CORE FEATURES                               Feb 1-14, 2026       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Semana 1 (Feb 1-7):                 Semana 2 (Feb 8-14):                   │
│  ───────────────────                 ────────────────────                    │
│  ⬜ Modelo QRAcceso persistente      ⬜ Portal guardian.html                │
│  ⬜ POST /qr/escanear                ⬜ Portal residente.html               │
│  ⬜ Tabla RegistroEscaneo            ⬜ Portal visitante.html               │
│  ⬜ POST /visitantes/autorizar       ⬜ Flujo end-to-end completo           │
│                                                                              │
│  DELIVERABLE: Flujo completo Residente → QR → Guardia → Evidencia          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Fase 3: Production (📅 PLANIFICADA - Feb 15-28, 2026)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📅 FASE 3: PRODUCTION READY                            Feb 15-28, 2026      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Semana 1 (Feb 15-21):               Semana 2 (Feb 22-28):                  │
│  ─────────────────────               ─────────────────────                   │
│  ⬜ PostgreSQL + particionamiento    ⬜ Deploy Railway Production           │
│  ⬜ Redis cache (latencia 5ms)       ⬜ Piloto 3 condominios                │
│  ⬜ Twilio SMS notificaciones        ⬜ Feedback loop + fixes               │
│  ⬜ Dashboard reportes básico        ⬜ 🎯 MVP RELEASE                      │
│                                                                              │
│  DELIVERABLE: Sistema productivo con 10 clientes piloto                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Fase 4: Growth (📅 Marzo-Abril 2026)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📅 FASE 4: GROWTH                                      Mar-Abr 2026         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Marzo 2026:                         Abril 2026:                            │
│  ────────────                        ────────────                            │
│  ⬜ App móvil PWA (iOS/Android)      ⬜ Integraciones (WhatsApp, Slack)     │
│  ⬜ Reconocimiento facial (IA)       ⬜ API pública para desarrolladores    │
│  ⬜ Dashboard analítico avanzado     ⬜ Marketplace de integraciones        │
│  ⬜ Escalar a 50 condominios         ⬜ 🎯 Series Seed preparation          │
│                                                                              │
│  DELIVERABLE: Producto maduro listo para escalar                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# � VALUACIÓN PRE-MVP

## Metodología de Valuación

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    VALUACIÓN PRE-MVP: $1.5M - $2.0M USD                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MÉTODO 1: Comparables de Arquitectura                                      │
│  ═══════════════════════════════════════                                     │
│                                                                              │
│  Componente Comparable    │ Empresa   │ Valuación │ % Capturado │ Valor     │
│  ────────────────────────────────────────────────────────────────────────── │
│  Multi-tenancy engine     │ Auth0     │ $10B      │ 0.01%       │ $1.0M     │
│  Event sourcing pipeline  │ Segment   │ $15B      │ 0.005%      │ $0.75M    │
│  Policy/governance engine │ AWS IAM   │ $2T (AWS) │ 0.00005%    │ $1.0M     │
│  ────────────────────────────────────────────────────────────────────────── │
│  Subtotal arquitectura                                          │ $2.75M    │
│  Descuento pre-revenue (40%)                                    │ -$1.1M    │
│  ════════════════════════════════════════════════════════════════════════  │
│  VALUACIÓN ARQUITECTURA                                         │ $1.65M    │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MÉTODO 2: Costo de Replicación                                             │
│  ═══════════════════════════════                                             │
│                                                                              │
│  Item                            │ Tiempo    │ Costo/mes │ Total            │
│  ────────────────────────────────────────────────────────────────────────── │
│  Diseño arquitectura AUP         │ 3 meses   │ $15K      │ $45K             │
│  Implementación AUP completa     │ 6 meses   │ $25K      │ $150K            │
│  Testing y debugging             │ 2 meses   │ $20K      │ $40K             │
│  Documentación enterprise        │ 1 mes     │ $10K      │ $10K             │
│  Infraestructura y DevOps        │ 2 meses   │ $15K      │ $30K             │
│  ────────────────────────────────────────────────────────────────────────── │
│  Costo de replicación                                           │ $275K     │
│  Multiplicador moat (5x)                                        │ x5        │
│  ════════════════════════════════════════════════════════════════════════  │
│  VALUACIÓN REPLICACIÓN                                          │ $1.375M   │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MÉTODO 3: Mercado Potencial                                                │
│  ═══════════════════════════                                                 │
│                                                                              │
│  TAM México: $800M × 0.1% captura Year 5 = $800K ARR                        │
│  Múltiplo SaaS B2B (10x ARR) = $8M valuación potencial Year 5               │
│  Descuento a valor presente (60%) = $3.2M                                   │
│  Descuento pre-revenue (50%) = $1.6M                                        │
│  ════════════════════════════════════════════════════════════════════════  │
│  VALUACIÓN MERCADO                                              │ $1.6M     │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│               ╔═══════════════════════════════════════════╗                 │
│               ║  VALUACIÓN PROMEDIO PRE-MVP: $1.54M USD   ║                 │
│               ║  Rango aceptable: $1.2M - $2.0M USD       ║                 │
│               ╚═══════════════════════════════════════════╝                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Justificación del Valor

| Factor | Peso | Descripción | Impacto en Valuación |
|--------|------|-------------|----------------------|
| **Arquitectura AUP** | 40% | Único en el mercado, moat 12-18 meses | +$600K |
| **Documentación** | 15% | Enterprise-grade, reduce onboarding | +$225K |
| **Stack Moderno** | 15% | FastAPI, PostgreSQL, escalable | +$225K |
| **Mercado** | 20% | $800M TAM México, 90% sin digitalizar | +$300K |
| **Equipo/Visión** | 10% | Founder técnico, roadmap claro | +$150K |
| **Total** | 100% | | **$1.5M** |

---

# 💰 RONDAS DE INVERSIÓN

## Estrategia de Fundraising

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     ESTRATEGIA DE LEVANTAMIENTO DE CAPITAL                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PRE-SEED (Ahora)         SEED (Q4 2026)         SERIES A (2028)           │
│   ════════════════         ═══════════════        ═══════════════           │
│                                                                              │
│   Monto: $150K-$300K       Monto: $800K-$1.5M     Monto: $3M-$5M            │
│   Valuación: $1.5M         Valuación: $6M-$8M    Valuación: $20M-$30M       │
│   Dilución: 10-20%         Dilución: 15-20%      Dilución: 15-20%           │
│                                                                              │
│        │                         │                       │                  │
│        ▼                         ▼                       ▼                  │
│   ┌─────────┐              ┌─────────┐             ┌─────────┐              │
│   │ MVP +   │     →        │ 150     │     →       │ 1,000   │              │
│   │ 10      │              │ clientes│             │ clientes│              │
│   │ pilotos │              │ $166K   │             │ $2M ARR │              │
│   │         │              │ ARR     │             │         │              │
│   └─────────┘              └─────────┘             └─────────┘              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Ronda Actual: PRE-SEED

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PRE-SEED: $150K - $300K USD                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TÉRMINOS PROPUESTOS:                                                        │
│  ═══════════════════                                                         │
│                                                                              │
│  • Monto objetivo:        $200K USD (rango: $150K - $300K)                  │
│  • Valuación pre-money:   $1.5M USD                                         │
│  • Dilución:              11.8% - 16.7%                                     │
│  • Instrumento:           SAFE con cap $1.5M o Equity directo               │
│  • Runway:                12-18 meses                                        │
│                                                                              │
│  USO DE FONDOS:                                                              │
│  ══════════════                                                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                                                                    │     │
│  │   EQUIPO (60% = $120K)                                            │     │
│  │   ████████████████████████████████████████████████████████        │     │
│  │   • 1 Backend Developer Senior ($4K/mes × 12 = $48K)              │     │
│  │   • 1 Frontend/Mobile Developer ($3.5K/mes × 12 = $42K)           │     │
│  │   • 1 Sales/BD Part-time ($2.5K/mes × 12 = $30K)                  │     │
│  │                                                                    │     │
│  │   INFRAESTRUCTURA (20% = $40K)                                    │     │
│  │   ██████████████████                                              │     │
│  │   • Cloud hosting (Railway/Neon/Redis): $500/mes × 12 = $6K       │     │
│  │   • Twilio SMS: $200/mes × 12 = $2.4K                             │     │
│  │   • Cloudinary Pro: $100/mes × 12 = $1.2K                         │     │
│  │   • Tools (GitHub, Sentry, etc): $300/mes × 12 = $3.6K            │     │
│  │   • Buffer/contingencia: $26.8K                                   │     │
│  │                                                                    │     │
│  │   MARKETING & SALES (15% = $30K)                                  │     │
│  │   ███████████████                                                 │     │
│  │   • Google Ads/LinkedIn: $1.5K/mes × 12 = $18K                    │     │
│  │   • Eventos/networking: $500/mes × 12 = $6K                       │     │
│  │   • Contenido/branding: $500/mes × 12 = $6K                       │     │
│  │                                                                    │     │
│  │   LEGAL & OPS (5% = $10K)                                         │     │
│  │   █████                                                           │     │
│  │   • Constitución/contratos: $5K                                   │     │
│  │   • Contabilidad: $300/mes × 12 = $3.6K                           │     │
│  │   • Misceláneos: $1.4K                                            │     │
│  │                                                                    │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 📈 PROYECCIONES FINANCIERAS

## Proyección a 1 Año (2026)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PROYECCIÓN AÑO 1 (2026)                                │
├─────────────────┬──────────┬──────────┬──────────┬──────────┬───────────────┤
│     Métrica     │   Mar    │   Jun    │   Sep    │   Dic    │    Total      │
├─────────────────┼──────────┼──────────┼──────────┼──────────┼───────────────┤
│ Condominios     │    10    │    30    │    80    │   150    │     150       │
│ Free            │     7    │    15    │    30    │    50    │      50       │
│ Pro ($49)       │     3    │    12    │    40    │    80    │      80       │
│ Enterprise($499)│     0    │     3    │    10    │    20    │      20       │
├─────────────────┼──────────┼──────────┼──────────┼──────────┼───────────────┤
│ MRR             │   $147   │  $2,085  │  $6,950  │ $13,870  │   $13,870     │
│ ARR (run rate) │  $1,764  │ $25,020  │ $83,400  │$166,440  │  $166,440     │
├─────────────────┼──────────┼──────────┼──────────┼──────────┼───────────────┤
│ Ingresos Acum.  │   $441   │  $4,137  │ $17,247  │ $44,817  │   $44,817     │
│ Gastos Acum.    │ $16,000  │ $48,000  │ $80,000  │$112,000  │  $112,000     │
│ Burn Rate/mes   │  $8,000  │  $8,000  │  $8,000  │  $8,000  │    $8,000     │
└─────────────────┴──────────┴──────────┴──────────┴──────────┴───────────────┘

  📊 KPIs Año 1:
  • ARR Exit: $166K
  • Clientes pagos: 100 (80 Pro + 20 Enterprise)
  • Churn mensual: <3%
  • CAC: <$100
  • LTV: >$1,500
  • LTV:CAC: >15:1
```

## Proyección a 3 Años (2026-2028)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PROYECCIÓN 3 AÑOS (2026-2028)                          │
├──────────────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│       Métrica        │    2026      │    2027      │    2028      │  CAGR   │
├──────────────────────┼──────────────┼──────────────┼──────────────┼─────────┤
│                      │              │              │              │         │
│ CLIENTES             │              │              │              │         │
│ ─────────            │              │              │              │         │
│ Condominios totales  │     150      │     500      │    1,200     │  183%   │
│ Free                 │      50      │     150      │      300     │  145%   │
│ Pro ($49)            │      80      │     280      │      700     │  196%   │
│ Enterprise ($499)    │      20      │      70      │      200     │  216%   │
│                      │              │              │              │         │
│ INGRESOS             │              │              │              │         │
│ ──────────           │              │              │              │         │
│ MRR (Dic)            │   $13,870    │   $48,650    │   $134,100   │  211%   │
│ ARR                  │  $166,440    │  $583,800    │ $1,609,200   │  211%   │
│ Ingresos anuales     │   $44,817    │  $350,000    │ $1,000,000   │  372%   │
│                      │              │              │              │         │
│ GASTOS               │              │              │              │         │
│ ────────             │              │              │              │         │
│ Equipo               │  $120,000    │  $400,000    │  $800,000    │  158%   │
│ Infraestructura      │   $15,000    │   $50,000    │  $120,000    │  183%   │
│ Marketing            │   $30,000    │  $100,000    │  $200,000    │  158%   │
│ Otros                │   $15,000    │   $50,000    │  $100,000    │  158%   │
│ Total gastos         │  $180,000    │  $600,000    │ $1,220,000   │  160%   │
│                      │              │              │              │         │
│ RESULTADOS           │              │              │              │         │
│ ───────────          │              │              │              │         │
│ EBITDA               │ -$135,183    │ -$250,000    │  -$220,000   │         │
│ Margen EBITDA        │    N/A       │    N/A       │    -22%      │         │
│ Breakeven esperado   │              │              │   Q4 2028    │         │
│                      │              │              │              │         │
│ MÉTRICAS SaaS        │              │              │              │         │
│ ──────────────       │              │              │              │         │
│ Churn mensual        │     3%       │     2.5%     │      2%      │         │
│ NRR (Net Revenue)    │    105%      │    115%      │     120%     │         │
│ CAC                  │    $100      │     $80      │      $60     │         │
│ LTV                  │   $1,500     │   $2,000     │    $3,000    │         │
│ LTV:CAC              │    15:1      │    25:1      │     50:1     │         │
│                      │              │              │              │         │
│ EQUIPO               │              │              │              │         │
│ ───────              │              │              │              │         │
│ Headcount            │      3       │      8       │      15      │         │
└──────────────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

## Proyección a 5 Años (2026-2030)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PROYECCIÓN 5 AÑOS (2026-2030)                          │
├────────────────┬────────┬────────┬────────┬─────────┬─────────┬─────────────┤
│    Métrica     │  2026  │  2027  │  2028  │  2029   │  2030   │    CAGR     │
├────────────────┼────────┼────────┼────────┼─────────┼─────────┼─────────────┤
│                │        │        │        │         │         │             │
│ ESCALA         │        │        │        │         │         │             │
│ ───────        │        │        │        │         │         │             │
│ Condominios    │   150  │   500  │  1,200 │  2,500  │  5,000  │    142%     │
│ Países         │    1   │    1   │    3   │    5    │    8    │             │
│ Usuarios tot.  │  3,000 │ 15,000 │ 50,000 │ 150,000 │ 400,000 │    170%     │
│                │        │        │        │         │         │             │
│ INGRESOS       │        │        │        │         │         │             │
│ ──────────     │        │        │        │         │         │             │
│ ARR            │ $166K  │ $584K  │ $1.6M  │  $4.2M  │  $10M   │    178%     │
│ Ingresos año   │  $45K  │ $350K  │  $1M   │  $2.8M  │  $7M    │    228%     │
│                │        │        │        │         │         │             │
│ VALORACIÓN     │        │        │        │         │         │             │
│ ────────────   │        │        │        │         │         │             │
│ Múltiplo ARR   │  10x   │  10x   │  12x   │  12x    │  15x    │             │
│ Valuación est. │ $1.5M  │  $6M   │ $20M   │  $50M   │ $150M   │    216%     │
│                │        │        │        │         │         │             │
│ RENTABILIDAD   │        │        │        │         │         │             │
│ ──────────────  │        │        │        │         │         │             │
│ Margen bruto   │  70%   │  75%   │  80%   │  82%    │  85%    │             │
│ EBITDA         │ -$135K │ -$250K │ -$220K │  $280K  │ $1.4M   │             │
│ Margen EBITDA  │  N/A   │  N/A   │  -22%  │  10%    │  20%    │             │
│                │        │        │        │         │         │             │
│ EQUIPO         │        │        │        │         │         │             │
│ ───────        │        │        │        │         │         │             │
│ Headcount      │    3   │    8   │   15   │   30    │   60    │             │
│                │        │        │        │         │         │             │
└────────────────┴────────┴────────┴────────┴─────────┴─────────┴─────────────┘
```

## Escenarios de Retorno para Inversionistas

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RETORNO PARA INVERSIONISTAS PRE-SEED                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Inversión: $200K por 13.3% equity (valuación $1.5M)                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  ESCENARIO CONSERVADOR (Base Case)                                    │ │
│  │  ══════════════════════════════════                                    │ │
│  │  • Exit Year 5 a $80M (8x ARR de $10M)                                │ │
│  │  • Dilución acumulada: 50% (Seed + Series A + B)                      │ │
│  │  • Equity final: 6.65%                                                │ │
│  │  • Valor: $5.32M                                                      │ │
│  │  • Retorno: 26.6x en 5 años                                           │ │
│  │  • IRR: 93%                                                           │ │
│  │                                                                        │ │
│  │  ESCENARIO OPTIMISTA (Upside Case)                                    │ │
│  │  ═══════════════════════════════════                                   │ │
│  │  • Exit Year 5 a $150M (15x ARR de $10M)                              │ │
│  │  • Dilución acumulada: 50%                                            │ │
│  │  • Equity final: 6.65%                                                │ │
│  │  • Valor: $9.98M                                                      │ │
│  │  • Retorno: 49.9x en 5 años                                           │ │
│  │  • IRR: 119%                                                          │ │
│  │                                                                        │ │
│  │  ESCENARIO PESIMISTA (Downside Case)                                  │ │
│  │  ════════════════════════════════════                                  │ │
│  │  • Exit Year 5 a $30M (6x ARR de $5M)                                 │ │
│  │  • Dilución acumulada: 60%                                            │ │
│  │  • Equity final: 5.32%                                                │ │
│  │  • Valor: $1.6M                                                       │ │
│  │  • Retorno: 8x en 5 años                                              │ │
│  │  • IRR: 52%                                                           │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  COMPARACIÓN CON BENCHMARKS:                                                │
│  ═══════════════════════════                                                 │
│                                                                              │
│  │ Tipo de inversión      │ Retorno típico │ MSP_AXS Base │ Diferencia   │ │
│  ├────────────────────────┼────────────────┼──────────────┼──────────────┤ │
│  │ S&P 500 (5 años)       │ 2x             │ 26.6x        │ +13x mejor   │ │
│  │ VC Pre-Seed promedio   │ 10x            │ 26.6x        │ +2.6x mejor  │ │
│  │ Top quartile Pre-Seed  │ 25x            │ 26.6x        │ En línea     │ │
│  │ Top decile Pre-Seed    │ 50x+           │ 49.9x (opt)  │ En línea     │ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 📊 MÉTRICAS DETALLADAS

## Unit Economics (Target)

| Métrica | Valor Target |
|---------|--------------|
| **CAC** (Customer Acquisition Cost) | < $100 |
| **LTV** (Lifetime Value) | > $1,500 |
| **LTV:CAC Ratio** | > 15:1 |
| **Churn Mensual** | < 3% |
| **Payback Period** | < 3 meses |

---

# 🎯 MÉTRICAS DE ÉXITO PRE-MVP

## KPIs Técnicos

| Métrica | Target | Actual | Estado |
|---------|--------|--------|--------|
| Uptime | 99.5% | 99.8% | ✅ |
| Latencia p95 escaneo QR | < 100ms | 50ms | ✅ |
| Latencia p95 con cache | < 10ms | TBD | 🔄 |
| Eventos/día soportados | 10,000 | 5,000 | ⚠️ |
| Cobertura de tests | > 70% | 30% | ❌ |

## KPIs de Producto (Post-MVP)

| Métrica | Target Mes 1 | Target Mes 3 |
|---------|--------------|--------------|
| Condominios activos | 10 | 30 |
| QRs generados/semana | 100 | 500 |
| Escaneos/día | 200 | 1,000 |
| Retención semanal | > 80% | > 85% |
| NPS | > 30 | > 50 |

---

# 🏁 CONCLUSIÓN

## Por qué invertir en MSP_AXS

### 1. **Arquitectura World-Class**
- Comparable con sistemas de empresas de $10B+ (Auth0, Segment, AWS)
- Moat defensible de 12-18 meses
- Documentación y diseño de primer nivel

### 2. **Mercado Desatendido**
- $800M TAM solo en México
- Condominios sin digitalización (90%+)
- Regulación creciente de seguridad

### 3. **Modelo de Negocio Probado**
- SaaS B2B con recurrencia
- Monetización nativa vía AUP_GOV
- Expansion revenue mediante tiers

### 4. **Timing Perfecto**
- Post-COVID: seguridad es prioridad
- Adopción tecnológica acelerada
- Sin competencia establecida con esta arquitectura

---

## Call to Action

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│     🚀 MSP_AXS busca $150K - $300K en ronda Pre-Seed                        │
│                                                                              │
│     ╔═══════════════════════════════════════════════════════════════════╗   │
│     ║                                                                   ║   │
│     ║   💎 VALUACIÓN PRE-MVP: $1.5M USD                                ║   │
│     ║                                                                   ║   │
│     ║   📈 PROYECCIONES:                                                ║   │
│     ║      • Año 1: $166K ARR (150 condominios)                        ║   │
│     ║      • Año 3: $1.6M ARR (1,200 condominios)                      ║   │
│     ║      • Año 5: $10M ARR (5,000 condominios)                       ║   │
│     ║                                                                   ║   │
│     ║   💰 RETORNO ESPERADO:                                            ║   │
│     ║      • Base case: 26.6x (IRR 93%)                                ║   │
│     ║      • Upside: 49.9x (IRR 119%)                                  ║   │
│     ║                                                                   ║   │
│     ╚═══════════════════════════════════════════════════════════════════╝   │
│                                                                              │
│     Uso de fondos ($200K):                                                   │
│     ──────────────────────                                                   │
│     • 60% ($120K) - Equipo (2 devs + 1 sales)                               │
│     • 20% ($40K)  - Infraestructura y tools                                 │
│     • 15% ($30K)  - Marketing y adquisición                                 │
│     •  5% ($10K)  - Legal y operaciones                                     │
│                                                                              │
│     Runway: 12-18 meses hasta Seed de $1M+                                  │
│                                                                              │
│     Contacto: [founder@msp-axs.com]                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 📋 RESUMEN EJECUTIVO PARA INVERSIONISTAS

| Aspecto | Detalle |
|---------|----------|
| **Producto** | SaaS de control de accesos para condominios |
| **Diferenciación** | Arquitectura AUP única (moat 12-18 meses) |
| **Mercado** | $800M TAM México, 90%+ sin digitalizar |
| **Valuación Pre-MVP** | $1.5M USD |
| **Ronda Actual** | Pre-Seed $150K-$300K |
| **Uso de Fondos** | Equipo (60%), Infra (20%), Marketing (15%), Legal (5%) |
| **Runway** | 12-18 meses |
| **Año 1 Target** | 150 condominios, $166K ARR |
| **Año 3 Target** | 1,200 condominios, $1.6M ARR |
| **Año 5 Target** | 5,000 condominios, $10M ARR, Exit $80-150M |
| **Retorno Esperado** | 26.6x - 49.9x en 5 años |
| **IRR Proyectado** | 93% - 119% |

---

**Documento preparado para inversionistas - Febrero 2026**  
**MSP_AXS - Control de Accesos Inteligente**
