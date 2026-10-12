"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Item = { visita_id: string; estado_visita: string; fotos: number; capturada_en: string | null;
  salida_en: string | null; venceria_en: string | null; clasificacion: string; motivo: string };
type Report = { modo: "simulacion"; borrado_activado: false; plazo_propuesto_dias: number; fecha_corte: string;
  total_identificaciones: number; total_fotos: number; resumen: Record<string, number>; nota: string; items: Item[] };
const labels: Record<string, string> = { venceria: "Vencerían", vigente: "Vigentes", revision: "Requieren revisión", posterior_al_corte: "Capturadas después del corte" };
function today(days = 0) {
  const parts = new Intl.DateTimeFormat("en", { timeZone: "America/Mexico_City", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(Date.now() + days * 86400000));
  return ["year", "month", "day"].map(type => parts.find(part => part.type === type)?.value).join("-");
}
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString("es-MX", { timeZone: "America/Mexico_City" }) : "Sin dato";

export default function ReporteVencimientoIdentificaciones({ condominioId }: { condominioId: string }) {
  const { getToken } = useAuth();
  const [cutoff, setCutoff] = useState(today);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const generation = useRef(0);
  useEffect(() => () => { generation.current++; }, []);
  async function simulate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selectedDate = String(new FormData(event.currentTarget).get("fecha_corte") || cutoff);
    setCutoff(selectedDate);
    const current = ++generation.current;
    setBusy(true); setError(""); setReport(null); setPage(0);
    try {
      const token = await getToken();
      if (!token) throw new Error("Inicia sesión para consultar el reporte");
      const query = new URLSearchParams({ fecha_corte: selectedDate });
      const data = await api.get<Report>(`/reportes/${encodeURIComponent(condominioId)}/identificaciones-vencimiento?${query}`, token);
      if (current === generation.current) setReport(data);
    } catch (failure) {
      if (current === generation.current) setError(failure instanceof Error ? failure.message : "No se pudo generar la simulación");
    } finally { if (current === generation.current) setBusy(false); }
  }
  return <section className="rounded-xl border border-blue-800 bg-gray-900 p-4 space-y-4">
    <header><h2 className="text-lg font-semibold">Vencimiento de identificaciones</h2>
      <p className="mt-1 text-sm text-blue-200">Simulación · plazo propuesto de 30 días · no borra fotografías</p></header>
    <p className="text-sm text-gray-300">Calcula qué registros llegarían al plazo al terminar la fecha seleccionada, en horario de Ciudad de México. Con salida: 30 días desde la salida; sin salida: 30 días desde la captura.</p>
    <form onSubmit={simulate} className="flex flex-wrap items-end gap-3">
      <label className="text-sm">Fecha de corte
        <input name="fecha_corte" type="date" required value={cutoff} onChange={event => setCutoff(event.target.value)}
          className="mt-1 block min-h-12 rounded-lg border border-gray-600 bg-gray-950 px-3" /></label>
      <button disabled={busy} className="min-h-12 rounded-lg bg-blue-600 px-4 font-semibold disabled:opacity-50">{busy ? "Generando simulación…" : "Simular vencimiento"}</button>
      <button type="button" disabled={busy} onClick={() => setCutoff(today())} className="min-h-12 rounded-lg border border-gray-600 px-3 disabled:opacity-50">Hoy</button>
      <button type="button" disabled={busy} onClick={() => setCutoff(today(30))} className="min-h-12 rounded-lg border border-gray-600 px-3 disabled:opacity-50">Dentro de 30 días</button>
    </form>
    {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
    {busy && <p role="status" className="text-sm text-gray-300">Consultando registros; las fotos se conservan.</p>}
    {report && <>
      <p className="text-sm">Corte consultado: <strong>{report.fecha_corte}</strong> · {report.total_identificaciones} identificaciones · {report.total_fotos} fotos</p>
      {cutoff !== report.fecha_corte && <p role="status" className="text-sm text-amber-300">Cambiaste la fecha. Vuelve a simular para actualizar el resultado.</p>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries(labels).map(([status, label]) => <div key={status} className="rounded-lg border border-gray-600 p-3"><p className="text-2xl font-semibold">{report.resumen[status] ?? 0}</p><p className="text-sm text-gray-300">{label}</p></div>)}</div>
      <p className="text-xs text-gray-400">{report.nota}</p>
      {!report.items.length && <p role="status">No hay identificaciones registradas para este condominio.</p>}
      {report.items.slice(page * 25, (page + 1) * 25).map(item => <article key={item.visita_id} className="rounded-lg border border-gray-700 p-3 space-y-1 break-words">
        <h3 className="font-semibold">{item.visita_id} · {labels[item.clasificacion]}</h3>
        <p className="text-sm">{item.fotos} fotos · Estado: {item.estado_visita.replaceAll("_", " ")}</p>
        <p className="text-sm text-gray-300">Captura: {formatDate(item.capturada_en)} · Salida: {formatDate(item.salida_en)}</p>
        <p className="text-sm">Vencería: {formatDate(item.venceria_en)}</p>
        <p className="text-sm text-gray-300">{item.motivo}</p>
      </article>)}
      {report.items.length > 25 && <nav aria-label="Páginas de identificaciones" className="flex items-center gap-4">
        <button disabled={page === 0} onClick={() => setPage(value => value - 1)} className="min-h-12 disabled:opacity-40">Anterior</button>
        <span>{page + 1} / {Math.ceil(report.items.length / 25)}</span>
        <button disabled={(page + 1) * 25 >= report.items.length} onClick={() => setPage(value => value + 1)} className="min-h-12 disabled:opacity-40">Siguiente</button>
      </nav>}
    </>}
  </section>;
}
