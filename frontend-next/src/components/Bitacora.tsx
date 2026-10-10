"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Evento = { id: number; visita_id: string; fecha: string; actor_id: string; accion: string; resultado: string; motivo: string | null; estado: string | null; autorizada_por: string | null; proposito: string | null };
type Pagina = { items: Evento[]; siguiente: number | null; pendientes_entrega_condominio: number };

export default function Bitacora({ condominioId, visitaId }: { condominioId: string; visitaId?: string }) {
  const { getToken } = useAuth();
  const [pagina, setPagina] = useState<Pagina | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setPagina(null);
    async function cargar() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Inicia sesión para consultar la bitácora");
        const params = new URLSearchParams();
        if (cursor) params.set("antes_id", String(cursor));
        if (visitaId) params.set("visita_id", visitaId);
        const data = await api.get<Pagina>(`/bitacora/${encodeURIComponent(condominioId)}?${params}`, token);
        if (active) setPagina(data);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "No se pudo cargar la bitácora");
      } finally { if (active) setLoading(false); }
    }
    void cargar();
    return () => { active = false; };
  }, [condominioId, visitaId, cursor, revision, getToken]);
  return <section aria-label="Bitácora de accesos" className="space-y-3">
    <div className="flex justify-between gap-3"><h2 className="font-semibold">Bitácora de accesos</h2>
      <button className="text-blue-300" disabled={loading} onClick={() => { setCursor(null); setRevision(n => n + 1); }}>Actualizar</button></div>
    <p className="text-xs text-gray-400">Eventos del condominio, del último recibido al primero. Horas en Ciudad de México.</p>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {loading && <p role="status">Cargando eventos…</p>}
    {pagina && <>
      {pagina.pendientes_entrega_condominio > 0 && <p role="status" className="text-amber-300">{pagina.pendientes_entrega_condominio} eventos del condominio pendientes de incorporarse. Actualiza en unos segundos.</p>}
      {pagina.items.length === 0 && <p>Sin eventos recibidos.</p>}
      {pagina.items.map(e => <article key={e.id} className="rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-2 break-words">
        <div className="flex justify-between gap-3"><strong>{e.motivo || e.accion}</strong><span className={e.resultado === "exito" ? "text-green-300" : "text-amber-300"}>{e.resultado === "exito" ? "Registrado" : "Rechazado / fallo"}</span></div>
        <p className="text-sm">{new Date(e.fecha).toLocaleString("es-MX", { timeZone: "America/Mexico_City" })} · Actor: {e.actor_id}</p>
        <p className="text-xs text-gray-400">Visita: {e.visita_id}{e.estado ? ` · ${e.estado.replaceAll("_", " ")}` : ""}</p>
        {e.autorizada_por && <p className="text-sm">Autorizó: {e.autorizada_por}</p>}
        {e.proposito && <p className="text-sm">Propósito: {e.proposito}</p>}
      </article>)}
      <div className="flex gap-4">
        {cursor && <button onClick={() => setCursor(null)} className="text-blue-300">Más recientes</button>}
        {pagina.siguiente && <button onClick={() => setCursor(pagina.siguiente)} className="text-blue-300">Anteriores</button>}
      </div>
    </>}
  </section>;
}
