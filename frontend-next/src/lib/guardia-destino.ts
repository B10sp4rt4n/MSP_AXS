import type { CasaItem, Visita } from "./types";
const normalizar = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
export function buscarDestinos(casas: CasaItem[], consulta: string) {
  const q = normalizar(consulta);
  if (!q) return [];
  return casas.filter(c => {
    const miembros = c.residentes ?? (c.residente ? [c.residente] : []);
    const texto = normalizar(`${c.numero} ${c.tipo} ${c.descripcion ?? ""} ${miembros.map(r => r.nombre).join(" ")}`);
    return q.split(/\s+/).every(p => texto.includes(p));
  });
}
export function visitaEnDestino(visita: Visita, casa: CasaItem) {
  // A catalog ID is authoritative; text is only a fallback for legacy visits.
  return visita.destino_id ? visita.destino_id === casa.casa_id : normalizar(visita.casa_unidad ?? "") === normalizar(casa.numero);
}
export function nombreDestino(casa: CasaItem) {
  return ["casa", "depto", "local"].includes(casa.tipo) ? `${casa.tipo === "depto" ? "Departamento" : casa.tipo === "local" ? "Local" : "Casa"} ${casa.numero}` : casa.numero;
}
