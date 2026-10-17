import type { Visita } from "./types";

const zona = "America/Mexico_City";
const dia = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit" });
export function instante(valor: string | null): number | null {
  if (!valor) return null;
  // CORE historically stored UTC without an offset.
  const n = Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/i.test(valor) ? valor : `${valor}Z`);
  return Number.isFinite(n) ? n : null;
}
export function horaPresencia(valor: string): string {
  const n = instante(valor);
  return n === null ? "Fecha no válida" : new Date(n).toLocaleString("es-MX", { timeZone: zona, dateStyle: "short", timeStyle: "short" });
}
export function resumirPresencia(visitas: Visita[], ahora: number) {
  const hoy = dia.format(ahora);
  const dentro: Visita[] = [];
  const revisar: Visita[] = [];
  let entradasHoy = 0, salidasHoy = 0;
  let ultimo: { visita: Visita; tipo: "Entrada" | "Salida"; fecha: string; instante: number } | null = null;
  for (const v of visitas) {
    const entrada = instante(v.entrada_registrada_en), salida = instante(v.salida_registrada_en);
    const inconsistente = (!!v.entrada_registrada_en && entrada === null)
      || (!!v.salida_registrada_en && salida === null)
      || (entrada !== null && entrada > ahora) || (salida !== null && salida > ahora)
      || (salida !== null && (entrada === null || salida < entrada))
      || (v.estado === "entrada_registrada" && (entrada === null || salida !== null))
      || (v.estado === "salida_registrada" && salida === null)
      || (entrada !== null && salida === null && v.estado !== "entrada_registrada");
    if (inconsistente) { revisar.push(v); continue; }
    if (entrada !== null && salida === null) dentro.push(v);
    if (entrada !== null && dia.format(entrada) === hoy) entradasHoy++;
    if (salida !== null && dia.format(salida) === hoy) salidasHoy++;
    const movimiento = salida ?? entrada;
    if (movimiento !== null && (!ultimo || movimiento > ultimo.instante)) {
      ultimo = { visita: v, tipo: salida !== null ? "Salida" : "Entrada", fecha: (salida !== null ? v.salida_registrada_en : v.entrada_registrada_en)!, instante: movimiento };
    }
  }
  dentro.sort((a,b) => instante(a.entrada_registrada_en)! - instante(b.entrada_registrada_en)!);
  return { dentro, revisar, entradasHoy, salidasHoy, ultimo };
}
