"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import Bitacora from "@/components/Bitacora";

type Evento = { id: number; fecha: string; visita_id: string; actor_id: string; categoria: string;
  accion: string; resultado: string; estado: string | null; destino: string | null; motivo: string | null };
type Reporte = { condominio_id: string; condominio: string; desde: string; hasta: string; generado_en: string;
  pendientes_entrega_condominio: number; total: number; resumen: Record<string, number>; items: Evento[] };
const labels: Record<string, string> = { entrada: "Entradas", salida: "Salidas", cancelacion: "Cancelaciones", rechazo: "Operaciones rechazadas", otro: "Otros eventos" };
const fecha = (value: string) => new Date(value).toLocaleString("es-MX", { timeZone: "America/Mexico_City" });
const inputClass = "w-full rounded-lg border border-gray-600 bg-gray-900 p-2 text-white";

function hoy() {
  const parts = new Intl.DateTimeFormat("en", { timeZone: "America/Mexico_City", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  return ["year", "month", "day"].map(type => parts.find(p => p.type === type)?.value).join("-");
}

export default function ReportesOperacion({ condominioId }: { condominioId: string }) {
  const { getToken } = useAuth();
  const [filtros, setFiltros] = useState(() => ({ desde: hoy(), hasta: hoy(), estado: "", destino: "", actor_id: "" }));
  const [reporte, setReporte] = useState<Reporte | null>(null);
  const [consulta, setConsulta] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [visita, setVisita] = useState<string | null>(null);
  const generation = useRef(0);
  useEffect(() => () => { generation.current++; }, []);
  function parametros() {
    return new URLSearchParams(Object.entries(filtros).filter(([, value]) => value !== "")).toString();
  }
  async function consultar() {
    const current = ++generation.current;
    setOcupado(true); setError(""); setReporte(null); setVisita(null); setPagina(0);
    try {
      const token = await getToken();
      if (!token) throw new Error("Inicia sesión para consultar reportes");
      const query = parametros();
      const data = await api.get<Reporte>(`/reportes/${encodeURIComponent(condominioId)}/operacion?${query}`, token);
      if (current === generation.current) { setReporte(data); setConsulta(query); }
    } catch (e) {
      if (current === generation.current) setError(e instanceof Error ? e.message : "No se pudo consultar el reporte");
    } finally { if (current === generation.current) setOcupado(false); }
  }
  async function descargar(formato: "xlsx" | "pdf") {
    const current = generation.current;
    setOcupado(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Inicia sesión para descargar reportes");
      const blob = await api.download(`/reportes/${encodeURIComponent(condominioId)}/operacion?${consulta}&formato=${formato}`, token);
      if (current !== generation.current) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `AXS-operacion-${reporte?.desde}-${reporte?.hasta}.${formato}`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      if (current === generation.current) setError(e instanceof Error ? e.message : "No se pudo descargar");
    } finally { if (current === generation.current) setOcupado(false); }
  }
  const cambio = reporte !== null && parametros() !== consulta;
  return <section aria-label="Reportes de operación" className="space-y-5">
    <div><h2 className="text-xl font-semibold">Reporte de operación diaria</h2>
      <p className="text-sm text-gray-400 mt-2">Movimientos registrados en el periodo. Fechas y horas de Ciudad de México. Hasta 31 días por consulta.</p></div>
    <form onSubmit={e => { e.preventDefault(); void consultar(); }} className="space-y-3">
      <fieldset disabled={ocupado} className="grid grid-cols-1 sm:grid-cols-2 gap-3 disabled:opacity-60">
        <label>Desde<input required type="date" className={inputClass} value={filtros.desde} onChange={e => setFiltros({ ...filtros, desde: e.target.value })} /></label>
        <label>Hasta<input required type="date" min={filtros.desde} className={inputClass} value={filtros.hasta} onChange={e => setFiltros({ ...filtros, hasta: e.target.value })} /></label>
        <label>Estado del evento<select className={inputClass} value={filtros.estado} onChange={e => setFiltros({ ...filtros, estado: e.target.value })}>
          <option value="">Todos</option>{["pendiente", "activa", "entrada_registrada", "salida_registrada", "cancelada"].map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></label>
        <label>Destino exacto<input className={inputClass} maxLength={200} placeholder="Ej. 101; vacío para todos" value={filtros.destino} onChange={e => setFiltros({ ...filtros, destino: e.target.value })} /></label>
        <label>Responsable (ID)<input className={inputClass} maxLength={200} placeholder="Vacío para todos" value={filtros.actor_id} onChange={e => setFiltros({ ...filtros, actor_id: e.target.value })} /></label>
      </fieldset>
      <button disabled={ocupado} className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50">{ocupado ? "Procesando…" : "Consultar reporte"}</button>
    </form>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {cambio && <p role="status" className="text-amber-200">Cambiaste los filtros. Consulta nuevamente para actualizar el reporte y las descargas.</p>}
    {reporte && <>
      <p className="text-sm text-gray-300">{reporte.condominio} · {reporte.desde} a {reporte.hasta}<br />Consultado: {fecha(reporte.generado_en)}</p>
      {reporte.pendientes_entrega_condominio > 0 && <p role="status" className="rounded-lg bg-amber-950 p-3 text-amber-200">Reporte provisional: {reporte.pendientes_entrega_condominio} eventos del condominio pendientes de incorporarse. Consulta nuevamente en unos segundos.</p>}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">{Object.entries(labels).map(([key, label]) => <div key={key} className="rounded-xl border border-gray-700 bg-gray-900 p-3"><p className="text-sm text-gray-300">{label}</p><strong className="text-2xl">{reporte.resumen[key]}</strong></div>)}</div>
      <p className="text-xs text-gray-400">Los rechazos incluyen operaciones de visita y QR. Estado y destino corresponden al evento; los datos ausentes no se infieren. Este reporte no confirma presencia física.</p>
      <div className="flex gap-3 flex-wrap">{(["xlsx", "pdf"] as const).map(f => <button key={f} disabled={ocupado || cambio} onClick={() => void descargar(f)} className="rounded-lg border border-gray-600 px-4 py-2 disabled:opacity-40">{f === "xlsx" ? "Descargar Excel" : "Descargar PDF carta"}</button>)}</div>
      <p className="text-xs text-gray-400">Las descargas vuelven a consultar con los filtros aplicados e incluyen su hora de generación.</p>
      <p>{reporte.total} eventos recibidos</p>
      {!reporte.total && <p>Sin eventos recibidos para este periodo y filtros.</p>}
      {reporte.items.slice(pagina * 25, (pagina + 1) * 25).map(e => <article key={e.id} className="rounded-xl border border-gray-700 p-4 space-y-2 break-words">
        <p className="font-semibold">{e.categoria === "otro" ? e.accion : labels[e.categoria]} · {e.resultado}</p>
        <p className="text-sm">{fecha(e.fecha)} · Responsable: {e.actor_id}</p>
        <p className="text-sm">Destino: {e.destino ?? "Sin dato"} · Estado del evento: {e.estado?.replaceAll("_", " ") ?? "Sin dato"}</p>
        {e.motivo && <p className="text-sm text-gray-300">{e.motivo}</p>}
        <button onClick={() => setVisita(e.visita_id)} className="text-blue-300 text-sm underline">Ver historial: {e.visita_id}</button>
      </article>)}
      {reporte.total > 25 && <nav aria-label="Páginas del reporte" className="flex gap-4 items-center">
        <button disabled={!pagina} onClick={() => setPagina(pagina - 1)} className="disabled:opacity-40">Anterior</button>
        <span>{pagina + 1} / {Math.ceil(reporte.total / 25)}</span>
        <button disabled={(pagina + 1) * 25 >= reporte.total} onClick={() => setPagina(pagina + 1)} className="disabled:opacity-40">Siguiente</button>
      </nav>}
      {visita && <aside className="border-t border-gray-600 pt-4 space-y-3"><h3>Historial completo: {visita}</h3><button onClick={() => setVisita(null)} className="text-blue-300">Cerrar historial</button><Bitacora key={visita} condominioId={condominioId} visitaId={visita} /></aside>}
    </>}
  </section>;
}
