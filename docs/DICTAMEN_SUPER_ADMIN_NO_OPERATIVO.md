# Dictamen Arquitectónico: Dominio Super Admin No Operativo

**Fecha:** 1 de enero de 2026  
**Sistema:** MSP_AXS  
**Alcance:** Evaluación de complejidad para agregar dominio meta-operativo

---

## 1. Evaluación de Complejidad

### **BAJA** ✅

**Justificación:**

La propuesta NO introduce una excepción al modelo existente, sino un **plano ortogonal** que lo complementa. Analizo por qué:

| Aspecto | Impacto |
|---------|---------|
| **RLS** | Intacto. El Super Admin NO entra a flujos con tenant activo |
| **Modelo de autorización** | Intacto. No hay bypass; hay un dominio separado |
| **Flujos operativos** | Intactos. Después de asignar relación, el sistema existente toma control |
| **Tablas operativas** | Sin modificaciones |

La complejidad es baja porque:
1. **El dominio es pequeño**: Solo 3 acciones (asignar, revocar, listar)
2. **El dominio es cerrado**: No necesita conocer la lógica interna de los tenants
3. **El límite es claro**: Termina en el momento que se crea la relación Identidad↔Tenant

---

## 2. Impacto por Dimensión

### **2.1 Modelo Mental del Sistema**

| Antes | Después |
|-------|---------|
| Un plano: operativo (dentro de tenant) | Dos planos: meta-operativo + operativo |
| Toda identidad existe en contexto tenant | Identidad existe primero; luego se vincula a tenant(s) |

**Impacto: BAJO**  
El modelo mental se enriquece, no se contradice. La separación es intuitiva:
- *"Primero te asigno a un condominio, luego actúas dentro de él"*

### **2.2 Seguridad**

**Impacto: NEUTRAL → POSITIVO**

| Riesgo | Mitigación natural |
|--------|---------------------|
| Escalación de privilegios | No existe. Super Admin no puede operar dentro de tenant |
| Bypass de RLS | Imposible. El dominio meta-operativo no toca tablas operativas |
| Acceso lateral entre tenants | No cambia. La asignación es declarativa, no transitiva |

**Ganancia:** La responsabilidad de asignar/revocar queda en un actor específico con trazabilidad propia, no mezclada con operaciones de negocio.

### **2.3 Trazabilidad**

**Impacto: POSITIVO**

Las acciones meta-operativas generan su propia línea de eventos:

```
AUP_EVENT {
    entidad: "RELACION_IDENTITY_TENANT"
    accion: "ASIGNAR" | "REVOCAR"
    identity: Super Admin
    target_identity: Usuario afectado
    target_tenant: Condominio
    resultado: PERMITIDO | DENEGADO
}
```

**Separación de auditoría:** Quién puede operar vs quién asignó el permiso para operar son trazas distintas y verificables independientemente.

### **2.4 RLS**

**Impacto: NULO**

El dominio meta-operativo opera sobre tablas de **relación** (tipo junction), no sobre tablas operativas con RLS.

```
┌─────────────────────────────────────────────────────────┐
│  DOMINIO META-OPERATIVO                                 │
│  • Tabla: identity_tenant_assignments                   │
│  • RLS: No aplica (no hay tenant_id como filtro)        │
│  • El filtro es: authority_id del Super Admin           │
└─────────────────────────────────────────────────────────┘
                         │
                         │ crea registro
                         ▼
┌─────────────────────────────────────────────────────────┐
│  DOMINIO OPERATIVO (existente)                          │
│  • Tabla: user_tenant_scope                             │
│  • RLS: tenant_id = current_setting('app.tenant_id')    │
│  • El sistema existente toma control desde aquí         │
└─────────────────────────────────────────────────────────┘
```

### **2.5 Riesgo de Errores Humanos**

**Impacto: MEDIO** (requiere atención)

| Error potencial | Consecuencia | Prevención |
|-----------------|--------------|------------|
| Super Admin se asigna a sí mismo a un tenant | Mezcla de roles | Regla: Super Admin no puede tener scopes operativos |
| Revocar sin verificar dependencias | Usuario pierde acceso en cascada | Soft-delete con período de gracia |
| Confundir "asignar relación" con "dar permisos" | Expectativa incorrecta | El sistema solo crea el vínculo; los permisos internos son del FIRST_TIER |

---

## 3. Elementos Nuevos Mínimos

### **3.1 Entidad de Relación**

```
IDENTITY_TENANT_ASSIGNMENT {
    assignment_id
    identity_id          → Usuario
    tenant_id            → Condominio
    assigned_by          → Super Admin que asignó
    assigned_at
    revoked_at?
    revocation_reason?
}
```

### **3.2 Enumeración de Acciones Meta-Operativas**

```
META_ACTION {
    ASSIGN_IDENTITY_TO_TENANT
    REVOKE_IDENTITY_FROM_TENANT
    LIST_TENANT_ASSIGNMENTS
    LIST_IDENTITY_ASSIGNMENTS
}
```

### **3.3 Validador de Dominio**

Función que verifica:
- El actor tiene authority de tipo `PLATFORM_ADMIN` (o similar)
- La acción es meta-operativa (no operativa)
- No hay conflicto de roles (Super Admin ≠ usuario operativo)

### **3.4 Eventos Meta-Operativos**

Extensión natural de `AUP_EVENT` con:
- `entidad: ASSIGNMENT`
- Sin `tenant_id` de contexto (es cross-tenant por definición)
- Con `target_tenant_id` como dato del evento

---

## 4. Riesgos Principales de Implementación

### **4.1 Riesgo Crítico: Mezclar Dominios**

❌ **Error conceptual:**
```
"El Super Admin también puede ver reportes globales de todos los tenants"
```

**Por qué es peligroso:** Introduce la primera grieta. Si puede ver, eventualmente podrá actuar. El límite se difumina.

✅ **Principio correcto:** El Super Admin es ciego al contenido operativo. Solo ve relaciones.

### **4.2 Riesgo Alto: Reutilizar Infraestructura Operativa**

❌ **Error técnico:**
```
"Usamos el mismo middleware de tenant para el Super Admin"
```

**Por qué es peligroso:** Fuerza un `tenant_id = NULL` o un tenant especial, lo cual es un bypass encubierto.

✅ **Principio correcto:** Rutas meta-operativas usan un middleware **distinto** que no inyecta tenant.

### **4.3 Riesgo Medio: Confusión de Responsabilidades**

❌ **Error organizacional:**
```
"El Super Admin también define qué permisos tiene cada rol dentro del tenant"
```

**Por qué es peligroso:** Eso es responsabilidad del FIRST_TIER. Cruzar ese límite elimina la autonomía del tenant y centraliza poder.

✅ **Principio correcto:** Super Admin asigna la relación. Los permisos internos son del dueño del tenant.

### **4.4 Riesgo Bajo: Over-Engineering**

❌ **Error de implementación:**
```
"Necesitamos un microservicio separado para el dominio meta-operativo"
```

**Por qué es innecesario:** Son 3 acciones sobre 1 tabla. Un módulo/router aislado es suficiente.

---

## 5. Dictamen Final

### **5.1 Coherencia con el Sistema**

| Pilar del Sistema | ¿La propuesta lo respeta? |
|-------------------|---------------------------|
| Toda operación ocurre dentro de tenant | ✅ Sí. El dominio meta NO es operativo |
| RLS sin bypasses | ✅ Sí. El dominio meta no toca tablas con RLS |
| Autorización por acción + contexto | ✅ Sí. Se agrega contexto "meta-operativo" |
| Trazabilidad de acción humana | ✅ Sí. Eventos separados y auditables |
| No existe super usuario omnipotente | ✅ Sí. Super Admin no puede operar, solo vincular |

### **5.2 ¿Extensión Natural o Fricción Estructural?**

**EXTENSIÓN NATURAL** ✅

La propuesta:
1. **No contradice** ningún axioma existente
2. **No modifica** la lógica operativa
3. **No introduce** excepciones de seguridad
4. **Sí completa** un vacío funcional: ¿quién crea la primera relación?

Actualmente el sistema asume que las relaciones `user_tenant_scope` ya existen. Esta capa responde estructuralmente a: **¿quién las crea y con qué autoridad?**

### **5.3 Valor vs Complejidad**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   VALOR                                                 │
│   ═════                                                 │
│   • Responde "quién asigna acceso" de forma auditable   │
│   • Separa gobierno de operación                        │
│   • Permite escalar sin modificar lógica operativa      │
│   • Habilita onboarding de clientes sin tocar código    │
│                                                         │
│   COMPLEJIDAD                                           │
│   ═══════════                                           │
│   • 1 tabla nueva                                       │
│   • 1 enum de acciones                                  │
│   • 1 router/módulo aislado                             │
│   • 3-4 funciones                                       │
│                                                         │
│   RATIO: Alto valor / Baja complejidad                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Conclusión Ejecutiva

| Pregunta | Respuesta |
|----------|-----------|
| ¿Es viable? | ✅ Sí |
| ¿Rompe el modelo? | ❌ No |
| ¿Introduce riesgo de seguridad? | ❌ No (si se implementa correctamente) |
| ¿Es proporcional al esfuerzo? | ✅ Sí |
| ¿Requiere rediseño? | ❌ No. Es aditivo |

**Recomendación:** Proceder con implementación, manteniendo estricta separación de dominios. El mayor riesgo no es técnico sino conceptual: **resistir la tentación de agregar "una cosita más" al Super Admin**.

El dominio debe nacer pequeño y morir pequeño.

---

## 7. Próximos Pasos Sugeridos

### **Fase 1: Diseño Detallado** (1-2 días)
- [ ] Definir esquema de tabla `identity_tenant_assignments`
- [ ] Especificar enum `MetaAction`
- [ ] Documentar límites estrictos del dominio

### **Fase 2: Implementación Core** (3-5 días)
- [ ] Crear tabla y migraciones
- [ ] Implementar 3 funciones básicas (asignar, revocar, listar)
- [ ] Agregar validaciones de dominio

### **Fase 3: Trazabilidad** (2-3 días)
- [ ] Integrar con AUP_EVENT
- [ ] Definir eventos meta-operativos
- [ ] Implementar auditoría específica

### **Fase 4: Testing y Documentación** (2-3 días)
- [ ] Tests unitarios de funciones meta-operativas
- [ ] Tests de separación de dominios
- [ ] Documentación de casos de uso
- [ ] Guía de uso para operadores

**Estimación total:** 8-13 días de desarrollo

---

## 8. Restricciones Críticas (No Negociables)

1. **El Super Admin NUNCA opera dentro de un tenant**
2. **El Super Admin NO bypassa RLS**
3. **Las rutas meta-operativas usan middleware separado**
4. **Toda acción meta-operativa genera AUP_EVENT**
5. **El dominio meta NO crece más allá de asignaciones**

---

**Firmado:** Arquitecto Senior de Sistemas Multi-Tenant  
**Revisión:** Pendiente de aprobación por equipo de seguridad
