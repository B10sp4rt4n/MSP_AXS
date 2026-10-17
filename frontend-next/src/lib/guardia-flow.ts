import type { Visita } from "./types";
import { instante } from "./presencia";
import type { Reglas } from "@/components/ReglasAcceso";

export type Operacion = "entrada" | "salida";
export function abierta(v: Visita) {
  return v.estado === "entrada_registrada" && instante(v.entrada_registrada_en) !== null && !v.salida_registrada_en;
}
const normalizar = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
export function buscarVisitas(rows: Visita[], consulta: string, operacion: Operacion, historial = false) {
  const q = normalizar(consulta);
  if (q.length < 2) return [];
  return rows.filter(v => (historial || (operacion === "salida" ? abierta(v) : ["pendiente", "activa"].includes(v.estado)))
    && q.split(/\s+/).every(word => normalizar(`${v.nombre_visitante} ${v.casa_unidad ?? ""} ${v.visita_id} ${v.placa ?? ""}`).includes(word)));
}
export function evaluarVisita(v: Visita, op: Operacion, reglas: Reglas | null, qr: string | null, ahora = Date.now()) {
  const no = (mensaje: string) => ({ permitida: false, mensaje });
  const entrada = instante(v.entrada_registrada_en), salida = instante(v.salida_registrada_en);
  if ((v.entrada_registrada_en && entrada === null) || (v.salida_registrada_en && salida === null)
    || (entrada !== null && entrada > ahora) || (salida !== null && (entrada === null || salida < entrada || salida > ahora)))
    return no("Las horas de esta visita no coinciden. Solicita revisión a administración.");
  if (salida !== null) return no("Esta visita ya tiene salida registrada. No registres otra salida.");
  if (op === "salida") return abierta(v)
    ? { permitida: true, mensaje: "Entrada abierta. Confirma que esta es la persona que sale." }
    : no("No hay una entrada abierta para esta visita. Revisa el registro o solicita apoyo a administración.");
  if (entrada !== null) return no("Esta visita ya tiene entrada. Si la persona sale, usa Registrar salida.");
  if (!["pendiente", "activa"].includes(v.estado)) return no("Esta visita está cancelada o finalizada. Solicita una nueva autorización.");
  if (!reglas) return no("No pudimos comprobar las reglas de acceso. Actualiza la revisión antes de continuar.");
  const aplica = reglas.tipos_visita.includes(v.tipo_visita);
  if ((reglas.exigir_autorizacion || reglas.exigir_proposito) && !["eventual", "frecuente", "visita_personal", "proveedor", "entrega"].includes(v.tipo_visita))
    return no("El tipo de visita requiere revisión de administración.");
  if (aplica && reglas.exigir_proposito && !v.proposito?.trim()) return no(`Falta el propósito de la visita. Contacta a la vivienda ${v.casa_unidad} o a administración.`);
  if (aplica && reglas.exigir_autorizacion && (!v.autorizada_por || !v.autorizada_en)) return no(`Falta autorización. Contacta a la vivienda ${v.casa_unidad} o a administración.`);
  if (v.qr_token || (aplica && reglas.exigir_autorizacion)) {
    const fecha = instante(v.vigencia ?? null);
    if (fecha === null) return no("Falta una fecha válida de acceso. Solicita revisión a administración.");
    if (ahora < fecha - 30 * 60000) return no("Todavía no puede ingresar. Contacta al residente.");
    if (ahora >= fecha + 60 * 60000) return no("Necesita una nueva autorización. Contacta al residente.");
  }
  if (v.qr_token) {
    if (!qr || qr !== v.qr_token) return no("Esta visita requiere su QR. Pide al visitante que lo recupere con el residente; no crees otra visita para sustituirlo.");
    const hasta = instante(v.qr_vigencia ?? null);
    if (hasta === null || ahora >= hasta) return no("El QR venció. Solicita una nueva autorización de entrada.");
  }
  return { permitida: true, mensaje: "Puede ingresar. Confirma que es la persona que tienes enfrente." };
}
