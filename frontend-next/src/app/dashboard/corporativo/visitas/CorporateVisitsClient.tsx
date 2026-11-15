"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Visit = { visit_id: string; visitor_ref: string; state: string; host_user_id: string;
  created_at: string; authorized_at: string | null; entered_at: string | null; exited_at: string | null };
type Capabilities = { hosts: { user_id: string; nombre: string }[];
  can_authorize: boolean; can_record_movement: boolean };
type Destination = { destination_id: string; nombre: string };
type Log = { event_uid: string; action: string; timestamp: string };
type Command = { request_id: string; visitor_ref: string; host_user_id: string; destination_id: string };
const field = "w-full rounded-lg border border-gray-500 bg-gray-900 p-3 text-white";
const button = "min-h-12 rounded-lg bg-blue-700 px-4 py-3 text-white disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-blue-300";
const labels: Record<string, string> = { preregistrada: "Pendiente de autorización", autorizada: "Autorizada", dentro: "Dentro", cerrada: "Salida registrada", cancelada: "Cancelada" };
const actions: Record<string, string> = { autorizar: "Autorizar", entrada: "Registrar entrada", salida: "Registrar salida", cancelar: "Cancelar visita" };

export default function CorporateVisitsClient({ tenant, site }: { tenant: string; site: string }) {
  const { userId, isLoaded, getToken } = useAuth();
  const valid = /^corp_[A-Za-z0-9_-]{1,100}$/.test(tenant) && /^site_[A-Za-z0-9_-]{1,50}$/.test(site);
  return <main className="min-h-screen bg-gray-950 p-4 text-white sm:p-6">
    <div className="mx-auto max-w-4xl space-y-5">
      <h1 className="text-2xl font-bold">Visitas corporativas</h1>
      <a className="text-blue-300 underline" href={`/dashboard/corporativo?empresa=${encodeURIComponent(tenant)}`}>Volver al directorio</a>
      {!valid ? <p role="alert">Abre una sede desde el directorio corporativo.</p> : !isLoaded ? <p role="status">Comprobando sesión…</p>
        : !userId ? <p role="alert">Inicia sesión para continuar.</p>
        : <Board key={`${userId}:${tenant}:${site}`} tenant={tenant} site={site} getToken={getToken} />}
    </div>
  </main>;
}

function Board({ tenant, site, getToken }: { tenant: string; site: string; getToken: () => Promise<string | null> }) {
  const base = `/corporativo/${encodeURIComponent(tenant)}/sedes/${encodeURIComponent(site)}/visitas`;
  const [data, setData] = useState<{ visits: Visit[]; caps: Capabilities; destinations: Destination[] } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({ visitor_ref: "", host_user_id: "", destination_id: "" });
  const [pending, setPending] = useState<Command | null>(null);
  const [review, setReview] = useState<{ visit: Visit; action: string } | null>(null);
  const [log, setLog] = useState<Log[] | null>(null);
  const alive = useRef(true);
  const locked = useRef(false);
  async function token() { const value = await getToken(); if (!value) throw Error("Sesión no disponible"); return value; }
  async function read(signal?: AbortSignal) {
    const t = await token();
    const [caps, visits, destinations] = await Promise.all([
      api.get<Capabilities>(base + "/capacidades", t, signal), api.get<Visit[]>(base, t, signal),
      api.get<Destination[]>(`/corporativo/${encodeURIComponent(tenant)}/sedes/${encodeURIComponent(site)}/destinos`, t, signal),
    ]);
    if (alive.current && !signal?.aborted) setData({ caps, visits, destinations });
  }
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    read(controller.signal).catch(() => { if (!controller.signal.aborted) setError("Sede, sesión o módulo de visitas no disponible."); });
    return () => { alive.current = false; controller.abort(); };
    // Scope changes remount this component, including when the identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function run(work: () => Promise<void>) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(""); setLog(null);
    try { await work(); }
    catch { if (alive.current) { setData(null); setReview(null); setError("No pudimos confirmar la operación. Consulta las visitas o reintenta la misma solicitud antes de iniciar otra."); } }
    finally { locked.current = false; if (alive.current) setBusy(false); }
  }
  function create(event: FormEvent) {
    event.preventDefault();
    if (locked.current) return;
    const command = pending ?? { ...draft, request_id: crypto.randomUUID() };
    setPending(command);
    void run(async () => { await api.post<Visit>(base, command, await token());
      if (!alive.current) return; setPending(null); setDraft({ visitor_ref: "", host_user_id: "", destination_id: "" }); await read(); });
  }
  function confirm() {
    if (!review) return;
    const chosen = review;
    setReview(null);
    void run(async () => { await api.patch<Visit>(`${base}/${chosen.visit.visit_id}/${chosen.action}`, {}, await token()); await read(); });
  }
  return <>
    {error ? <p role="alert" className="rounded-lg border border-red-500 p-4">{error}</p> : null}
    <button className={button} disabled={busy} onClick={() => void run(() => read())}>Consultar visitas</button>
    {!data && !error ? <p role="status">Cargando sede y permisos…</p> : null}
    {data || pending ? <form onSubmit={create} className="space-y-3 rounded-xl border border-gray-700 p-4">
      <h2 className="text-xl font-semibold">Preregistrar visita</h2>
      <p className="text-sm text-gray-300">Usa un folio interno. No escribas nombres, correos ni documentos en la referencia.</p>
      <fieldset disabled={busy || !!pending || !data} className="space-y-3">
        <label className="block">Referencia de visita<input className={field} required pattern="[A-Za-z0-9_-]{1,80}" maxLength={80} value={draft.visitor_ref} onChange={e => setDraft({ ...draft, visitor_ref: e.target.value })} /></label>
        <label className="block" htmlFor="visit-host">Anfitrión</label><select id="visit-host" className={field} required value={draft.host_user_id} onChange={e => setDraft({ ...draft, host_user_id: e.target.value })}>
          <option value="">Seleccionar anfitrión</option>{data?.caps.hosts.map(h => <option key={h.user_id} value={h.user_id}>{h.nombre}</option>)}</select>
        <label className="block" htmlFor="visit-destination">Destino</label><select id="visit-destination" className={field} required value={draft.destination_id} onChange={e => setDraft({ ...draft, destination_id: e.target.value })}>
          <option value="">Seleccionar destino</option>{data?.destinations.map(d => <option key={d.destination_id} value={d.destination_id}>{d.nombre}</option>)}</select>
      </fieldset>
      <button className={button} disabled={busy || (!data && !pending)}>{pending ? "Reintentar misma solicitud" : "Crear preregistro"}</button>
    </form> : null}
    {review && data ? <section role="dialog" aria-modal="false" aria-labelledby="visit-review" className="space-y-3 rounded-xl border border-blue-400 p-4">
      <h2 id="visit-review" className="text-xl font-semibold">Confirmar movimiento</h2>
      <p>{actions[review.action]} · {review.visit.visitor_ref}</p>
      <button autoFocus className={button} disabled={busy} onClick={confirm}>Confirmar</button>{" "}
      <button className={button} disabled={busy} onClick={() => setReview(null)}>Volver</button>
    </section> : null}
    {data ? <section className="space-y-3"><h2 className="text-xl font-semibold">Últimas 50 visitas de esta sede</h2>
      {!data.visits.length ? <p>No hay visitas registradas.</p> : data.visits.map(v => <article key={v.visit_id} className="space-y-3 rounded-xl border border-gray-700 p-4">
        <h3 className="text-lg font-semibold">{v.visitor_ref}</h3><p>{labels[v.state] || v.state}</p>
        <p className="text-sm text-gray-300">Entrada: {v.entered_at ? v.entered_at + " UTC" : "Pendiente"} · Salida: {v.exited_at ? v.exited_at + " UTC" : "Pendiente"}</p>
        <div className="flex flex-wrap gap-3">
          {[(data.caps.can_authorize && v.state === "preregistrada") ? "autorizar" : "",
            (data.caps.can_record_movement && v.state === "autorizada") ? "entrada" : "",
            (data.caps.can_record_movement && v.state === "dentro") ? "salida" : "",
            (data.caps.can_authorize && ["preregistrada", "autorizada"].includes(v.state)) ? "cancelar" : ""].filter(Boolean).map(action =>
            <button className={button} key={action} disabled={busy} onClick={() => setReview({ visit: v, action })}>{actions[action]}</button>)}
          <button className={button} disabled={busy} onClick={() => void run(async () => { const entries = await api.get<Log[]>(`${base}/${v.visit_id}/bitacora`, await token()); if (alive.current) setLog(entries); })}>Ver bitácora de {v.visitor_ref}</button>
        </div>
      </article>)}
    </section> : null}
    {log ? <section className="space-y-2" aria-label="Bitácora de visita"><h2 className="text-xl font-semibold">Bitácora</h2>{log.map(row => <p key={row.event_uid}>{row.action} · {row.timestamp} UTC</p>)}</section> : null}
  </>;
}
