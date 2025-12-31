# ═══════════════════════════════════════════════════════════════════════════
# PSEUDOCÓDIGO AUP — CONTRATO DE EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════
#
# ADVERTENCIA:
#   Este NO es código ejecutable.
#   Es un contrato mental de cómo DEBE fluir una operación en AUP.
#   
# PROPÓSITO:
#   Prevenir interpretaciones incorrectas del modelo AUP.
#   Servir como referencia ontológica para desarrolladores.
#
# USO:
#   Pasar tal cual a Claude/Copilot/GPT como contexto de arquitectura.
#   NO agregar sintaxis de lenguaje específico.
#   NO optimizar.
#   NO simplificar.
#
# ═══════════════════════════════════════════════════════════════════════════

## 1️⃣ AUP_SESSION — EXISTENCIA TEMPORAL

"""
AXIOMA:
  Nada ocurre sin sesión.
  Toda autenticación deja huella.
"""

PROCESO: AUTENTICAR_USUARIO
  ENTRADA:
    credenciales (email, password)
  
  FLUJO:
    1. BUSCAR identidad en memoria permanente
       SI NO existe:
         REGISTRAR evento(AUTENTICACION_FALLIDA, motivo="identidad_inexistente")
         RETORNAR FALLO
    
    2. VALIDAR credencial contra hash almacenado
       SI NO coincide:
         REGISTRAR evento(AUTENTICACION_FALLIDA, motivo="credencial_invalida")
         RETORNAR FALLO
    
    3. CREAR sesión temporal:
       sesion.identity_id = identidad.id
       sesion.issued_at = AHORA()
       sesion.expires_at = AHORA() + DURACION_SESION
       sesion.method = "local"
    
    4. SERIALIZAR sesión como token opaco (JWT, cookie, etc.)
    
    5. REGISTRAR evento(AUTENTICACION_EXITOSA):
       actor = identidad.id
       metodo = "local"
       timestamp = AHORA()
       resultado = EXITO
    
    6. RETORNAR token
  
  SALIDA:
    token_sesion (opaco, no contiene alcance)

---

## 2️⃣ AUP_SCOPE — RESOLUCIÓN DE ALCANCE

"""
AXIOMA:
  El alcance no vive en el token.
  Vive en la memoria viva.
  Se resuelve en CADA operación.
"""

PROCESO: RESOLVER_SCOPE
  ENTRADA:
    sesion (validada previamente)
    tenant_id (contexto de operación)
    nivel_requerido (LECTURA | ESCRITURA | ADMIN)
  
  FLUJO:
    1. EXTRAER identity_id de sesión
    
    2. BUSCAR en memoria viva:
       scopes = QUERY(
         identity_id = sesion.identity_id
         AND tenant_id = tenant_id
         AND estado = ACTIVO
       )
    
    3. SI scopes está vacío:
       REGISTRAR evento(SCOPE_DENEGADO):
         actor = sesion.identity_id
         tenant = tenant_id
         motivo = "sin_scope_activo"
         resultado = DENEGADO
       
       RETORNAR DENEGADO
    
    4. PARA CADA scope EN scopes:
       SI scope.nivel >= nivel_requerido:
         RETORNAR PERMITIDO
    
    5. SI ningún scope cumple:
       REGISTRAR evento(SCOPE_INSUFICIENTE):
         actor = sesion.identity_id
         tenant = tenant_id
         nivel_requerido = nivel_requerido
         nivel_actual = MAX(scopes.nivel)
         resultado = DENEGADO
       
       RETORNAR DENEGADO
  
  SALIDA:
    PERMITIDO | DENEGADO

---

## 3️⃣ AUP_GOV — PLANO DE PODER

"""
AXIOMAS:
  1. El router no decide poder.
  2. El gobierno no ejecuta negocio.
  3. Default = DENY (si no hay política explícita, se deniega).
"""

PROCESO: EVALUAR_GOBIERNO
  ENTRADA:
    sesion (validada)
    accion (nombre de operación, ej: "generar_qr")
    tenant_id (contexto)
    metadata (ej: {dias_vigencia: 7})
  
  FLUJO:
    1. BUSCAR políticas aplicables:
       policies = QUERY(
         (ambito = GLOBAL OR (ambito = TENANT AND target = tenant_id))
         AND accion_objetivo = accion
         AND estado = ACTIVO
         AND valida_desde <= AHORA()
         AND (valida_hasta IS NULL OR valida_hasta >= AHORA())
       )
    
    2. SI policies está vacío:
       REGISTRAR evento(GOBIERNO_DENEGADO):
         actor = sesion.identity_id
         accion = accion
         motivo = "sin_politica_aplicable"
         resultado = DENEGADO
       
       RETORNAR DENEGADO, "No hay política que autorice esta acción"
    
    3. PARA CADA policy EN policies:
       SI policy.limites contiene restricciones:
         
         # Evaluar límite de cantidad
         SI "max_count" EN policy.limites:
           valor_actual = CONTAR(accion, tenant_id)
           SI valor_actual >= policy.limites.max_count:
             REGISTRAR evento(GOBIERNO_DENEGADO):
               actor = sesion.identity_id
               accion = accion
               motivo = "limite_excedido"
               limite = policy.limites.max_count
               valor_actual = valor_actual
               resultado = DENEGADO
             
             RETORNAR DENEGADO, "Límite excedido"
         
         # Evaluar límite de vigencia
         SI "max_dias_vigencia" EN policy.limites:
           dias_solicitados = metadata.dias_vigencia
           SI dias_solicitados > policy.limites.max_dias_vigencia:
             REGISTRAR evento(GOBIERNO_DENEGADO):
               actor = sesion.identity_id
               accion = accion
               motivo = "vigencia_excedida"
               limite = policy.limites.max_dias_vigencia
               solicitado = dias_solicitados
               resultado = DENEGADO
             
             RETORNAR DENEGADO, "Vigencia excedida"
    
    4. VERIFICAR delegaciones (si aplica):
       delegation = BUSCAR_DELEGACION(
         authority = sesion.authority_id,
         permiso = accion,
         estado = ACTIVO,
         vigencia <= AHORA()
       )
       
       SI delegation existe:
         # La delegación permite ejecutar
         REGISTRAR evento(GOBIERNO_PERMITIDO):
           actor = sesion.identity_id
           accion = accion
           motivo = "delegacion_activa"
           delegation_id = delegation.id
           resultado = PERMITIDO
         
         RETORNAR PERMITIDO, "Autorizado por delegación"
    
    5. SI todas las evaluaciones pasaron:
       REGISTRAR evento(GOBIERNO_PERMITIDO):
         actor = sesion.identity_id
         accion = accion
         tenant = tenant_id
         policies_evaluadas = [policy.id for policy in policies]
         resultado = PERMITIDO
       
       RETORNAR PERMITIDO, "Autorizado por política"
  
  SALIDA:
    (PERMITIDO | DENEGADO, motivo)

---

## 4️⃣ AUP_EVENT — VERDAD HISTÓRICA

"""
AXIOMA:
  El evento no se corrige.
  Si se altera, se detecta.
"""

PROCESO: REGISTRAR_EVENTO
  ENTRADA:
    actor (identity_id)
    entidad (tipo: session | scope | policy | qr | visita)
    entidad_id (identificador único)
    accion (crear | modificar | revocar | validar | denegar)
    tenant_id (contexto)
    resultado (EXITO | DENEGADO | ERROR)
    metadata (contexto adicional)
  
  FLUJO:
    1. CONSTRUIR registro inmutable:
       evento.event_id = GENERAR_UUID()
       evento.actor = actor
       evento.entidad = entidad
       evento.entidad_id = entidad_id
       evento.accion = accion
       evento.tenant_id = tenant_id
       evento.resultado = resultado
       evento.metadata = SERIALIZAR(metadata)
       evento.timestamp = AHORA_UTC()
    
    2. CALCULAR hash de integridad:
       evento.hash = SHA256(
         evento.event_id +
         evento.actor +
         evento.entidad +
         evento.entidad_id +
         evento.accion +
         evento.timestamp +
         evento.resultado
       )
    
    3. INSERTAR en memoria append-only:
       # NO permite UPDATE ni DELETE
       # Solo INSERT
       APPEND(evento)
    
    4. SI inserción falla:
       # Registrar fallo en log externo (no en AUP_EVENT)
       LOG_CRITICO("Evento perdido", evento)
  
  SALIDA:
    evento.event_id

---

## 5️⃣ EJEMPLO COMPLETO: GENERAR_QR

"""
AXIOMA:
  El negocio ocurre después del poder, nunca antes.
"""

OPERACION: GENERAR_QR_PARA_VISITA
  ENTRADA:
    token_sesion (opaco)
    nombre_visitante (string)
    dias_vigencia (integer)
    tenant_id (string, condominio)
  
  FLUJO:
    # ─────────────────────────────────────────────────────────────
    # PASO 1: VALIDAR SESIÓN (AUP_SESSION)
    # ─────────────────────────────────────────────────────────────
    sesion = DESERIALIZAR_TOKEN(token_sesion)
    
    SI sesion.expires_at < AHORA():
      REGISTRAR evento(SESION_EXPIRADA):
        actor = sesion.identity_id
        accion = "generar_qr"
        resultado = ERROR
      
      RETORNAR ERROR(401, "Sesión expirada")
    
    SI sesion.identity_id NO existe en memoria:
      REGISTRAR evento(IDENTIDAD_INVALIDA):
        accion = "generar_qr"
        resultado = ERROR
      
      RETORNAR ERROR(401, "Identidad inválida")
    
    # ─────────────────────────────────────────────────────────────
    # PASO 2: RESOLVER ALCANCE (AUP_SCOPE)
    # ─────────────────────────────────────────────────────────────
    scope_permitido = RESOLVER_SCOPE(
      sesion = sesion,
      tenant_id = tenant_id,
      nivel_requerido = ESCRITURA
    )
    
    SI scope_permitido == DENEGADO:
      # Evento ya registrado en RESOLVER_SCOPE
      RETORNAR ERROR(403, "Sin alcance en este tenant")
    
    # ─────────────────────────────────────────────────────────────
    # PASO 3: EVALUAR GOBIERNO (AUP_GOV)
    # ─────────────────────────────────────────────────────────────
    gobierno_ok, motivo = EVALUAR_GOBIERNO(
      sesion = sesion,
      accion = "generar_qr",
      tenant_id = tenant_id,
      metadata = {dias_vigencia: dias_vigencia}
    )
    
    SI gobierno_ok == DENEGADO:
      # Evento ya registrado en EVALUAR_GOBIERNO
      RETORNAR ERROR(403, motivo)
    
    # ─────────────────────────────────────────────────────────────
    # PASO 4: EJECUTAR NEGOCIO (Solo ahora)
    # ─────────────────────────────────────────────────────────────
    qr_id = GENERAR_UUID()
    qr_token = GENERAR_TOKEN_ALEATORIO()
    vigencia_hasta = AHORA() + DIAS(dias_vigencia)
    
    INSERTAR en memoria(qrs):
      qr_id = qr_id
      visitante = nombre_visitante
      token = qr_token
      tenant_id = tenant_id
      creado_por = sesion.identity_id
      vigencia_hasta = vigencia_hasta
      estado = ACTIVO
      usado = false
    
    # ─────────────────────────────────────────────────────────────
    # PASO 5: REGISTRAR VERDAD (AUP_EVENT)
    # ─────────────────────────────────────────────────────────────
    REGISTRAR evento(QR_GENERADO):
      actor = sesion.identity_id
      entidad = "qr"
      entidad_id = qr_id
      accion = "crear"
      tenant_id = tenant_id
      resultado = EXITO
      metadata = {
        visitante: nombre_visitante,
        dias_vigencia: dias_vigencia,
        vigencia_hasta: vigencia_hasta
      }
    
    # ─────────────────────────────────────────────────────────────
    # PASO 6: RETORNAR RESULTADO
    # ─────────────────────────────────────────────────────────────
    RETORNAR EXITO({
      qr_id: qr_id,
      token: qr_token,
      vigencia_hasta: vigencia_hasta
    })

---

## 6️⃣ AXIOMA GLOBAL DE CIERRE

"""
DECLARACIÓN FINAL:

  No SESSION  → No acción
    Sin sesión válida, ninguna operación puede iniciarse.
    El sistema rechaza antes de consultar alcance o gobierno.
  
  No SCOPE    → No permiso
    Sin alcance en el tenant, la operación es imposible estructuralmente.
    No se evalúa gobierno si no hay alcance.
  
  No GOV OK   → No ejecución
    Sin aprobación del gobierno, el negocio no se ejecuta.
    Default = DENY (ausencia de política = denegación).
  
  No EVENT    → No existencia
    Si no hay evento registrado, la operación no ocurrió.
    El evento es la única fuente de verdad histórica.

ORDEN NO NEGOCIABLE:

  1. SESSION (¿Quién?)
  2. SCOPE (¿Dónde?)
  3. GOV (¿Puede?)
  4. NEGOCIO (Ejecutar)
  5. EVENT (Registrar verdad)

VIOLACIONES COMUNES A EVITAR:

  ❌ Colocar lógica de negocio ANTES de evaluar gobierno
     → Riesgo: Ejecución sin autorización
  
  ❌ Resolver scope DESPUÉS de evaluar gobierno
     → Riesgo: Gobierno evalúa sin contexto de tenant
  
  ❌ Registrar evento SOLO en éxito
     → Riesgo: Intentos fallidos invisibles (auditoría rota)
  
  ❌ Cachear resultado de gobierno por más de 1 minuto
     → Riesgo: Política revocada pero sistema sigue permitiendo
  
  ❌ Simplificar eliminando pasos "innecesarios"
     → Riesgo: Modelo AUP colapsa, sistema se convierte en monolito

ESTO NO ES BUROCRACIA.
ESTO ES ARQUITECTURA.

Si algo parece "demasiado complejo",
es porque el problema que resuelve ES complejo.

Simplificar rompe el modelo.
Mantener el orden garantiza la integridad.
"""

# ═══════════════════════════════════════════════════════════════════════════
# FIN DEL CONTRATO DE EJECUCIÓN AUP
# ═══════════════════════════════════════════════════════════════════════════
