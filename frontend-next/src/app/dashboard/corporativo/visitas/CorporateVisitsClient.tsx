"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import { corporateTime, validTimeZone } from "@/lib/corporate-time";
import { rememberCorporateWorkspace } from "@/lib/corporate-entry";

type Visit = { visit_id: string; visitor_ref: string; state: string; host_user_id: string; destination_id: string;
  created_at: string; authorized_at: string | null; entered_at: string | null; exited_at: string | null };
type Capabilities = { hosts: { user_id: string; nombre: string }[];
  can_authorize: boolean; can_record_movement: boolean };
type Destination = { destination_id: string; nombre: string };
type Site = { site_id: string; nombre: string; zona_horaria: string };
type Log = { event_uid: string; action: string; timestamp: string };
type Command = { request_id: string; visitor_ref: string; host_user_id: string; destination_id: string };
const field = "w-full rounded-lg border border-gray-500 bg-gray-900 p-3 text-white";
const button = "min-h-12 rounded-lg bg-blue-700 px-4 py-3 text-white disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-blue-300";
const labels: Record<string, string> = { preregistrada: "Pendiente de autorización", autorizada: "Autorizada", dentro: "Dentro", cerrada: "Salida registrada", cancelada: "Cancelada" };
const actions: Record<string, string> = { autorizar: "Autorizar", entrada: "Registrar entrada", salida: "Registrar salida", cancelar: "Cancelar visita" };
const events: Record<string, string> = { preregistrar: "Preregistro creado", autorizar: "Visita autorizada", entrada: "Entrada registrada", salida: "Salida registrada", cancelar: "Visita cancelada" };

function VisitTime({ value, zone }: { value: string | null; zone: string }) {
  if (!value) return <span>Pendiente</span>;
  const time = corporateTime(value, zone);
  if (!time) return <span>Fecha no válida</span>;
  return <span className="inline-flex min-w-0 max-w-full flex-col">
    <time className="[overflow-wrap:anywhere]" dateTime={time.utc}>{time.local} · {time.timeZone}</time>
    <span className="break-all text-xs text-gray-400">UTC: <time dateTime={time.utc}>{time.utc}</time></span>
  </span>;
}

export default function CorporateVisitsClient({ tenant, site }: { tenant: string; site: string }) {
  const { userId, isLoaded, getToken } = useAuth();
  const valid = /^corp_[A-Za-z0-9_-]{1,100}$/.test(tenant) && /^site_[A-Za-z0-9_-]{1,50}$/.test(site);
  return <main className="min-h-screen bg-gray-950 p-4 text-white sm:p-6">
    <div className="mx-auto max-w-4xl space-y-5">
      <h1 className="text-2xl font-bold">Visitas corporativas</h1>
      <a className="text-blue-300 underline" href={`/dashboard/corporativo?empresa=${encodeURIComponent(tenant)}`}>Volver al directorio</a>
      {!valid ? <p role="alert">Abre una sede desde el directorio corporativo.</p> : !isLoaded ? <p role="status">Comprobando sesión…</p>
        : !userId ? <p role="alert">Inicia sesión para continuar.</p>
        : <Board key={`${userId}:${tenant}:${site}`} userId={userId} tenant={tenant} site={site} getToken={getToken} />}
    </div>
  </main>;
}

function Board({ tenant, site, getToken, userId }: { tenant: string; site: string; getToken: () => Promise<string | null>; userId: string }) {
  const base = `/corporativo/${encodeURIComponent(tenant)}/sedes/${encodeURIComponent(site)}/visitas`;
  const [data, setData] = useState<{ visits: Visit[]; caps: Capabilities; destinations: Destination[]; site: Site } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({ visitor_ref: "", host_user_id: "", destination_id: "" });
  const [pending, setPending] = useState<Command | null>(null);
  const [review, setReview] = useState<{ visit: Visit; action: string } | null>(null);
  const [log, setLog] = useState<{ visitId: string; entries: Log[] } | null>(null);
  const alive = useRef(true);
  const locked = useRef(false);
  async function token() { const value = await getToken(); if (!value || !alive.current) throw Error("Sesión no disponible"); return value; }
  async function read(signal?: AbortSignal) {
    const t = await token();
    const [caps, visits, destinations, sites] = await Promise.all([
      api.get<Capabilities>(base + "/capacidades", t, signal), api.get<Visit[]>(base, t, signal),
      api.get<Destination[]>(`/corporativo/${encodeURIComponent(tenant)}/sedes/${encodeURIComponent(site)}/destinos`, t, signal),
      api.get<Site[]>(`/corporativo/${encodeURIComponent(tenant)}/sedes`, t, signal),
    ]);
    const selectedSite = sites.find(row => row.site_id === site);
    if (!selectedSite) throw Error("Sede no disponible");
    if (alive.current && !signal?.aborted) {
      rememberCorporateWorkspace(userId, { tenant, site });
      setData({ caps, visits, destinations, site: selectedSite });
    }
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
  function openLog(visit: Visit) {
    if (log?.visitId === visit.visit_id) { setLog(null); return; }
    void run(async () => {
      const entries = await api.get<Log[]>(`${base}/${visit.visit_id}/bitacora`, await token());
      if (alive.current) setLog({ visitId: visit.visit_id, entries });
    });
  }
  return <>
    {data ? <p className="text-sm text-gray-300">Sede: {data.site.nombre} · Zona horaria: {validTimeZone(data.site.zona_horaria) ? data.site.zona_horaria : "UTC (zona de sede no válida; revisa su configuración)"}. Todos los registros conservan su referencia UTC.</p> : null}
    {error ? <p role="alert" className="rounded-lg border border-red-500 p-4">{error}</p> : null}
    <button className={button} disabled={busy} onClick={() => void run(() => read())}>Consultar visitas</button>
    {!data && !error ? <p role="status">Cargando sede y permisos…</p> : null}
    {data || pending ? <form onSubmit={create} className="space-y-3 rounded-xl border border-gray-700 p-4">
      <h2 className="text-xl font-semibold">Preregistrar visita</h2>
      <p className="text-sm text-gray-300">Usa un folio interno. No escribas nombres, correos ni documentos en la referencia.</p>
      <fieldset disabled={busy || !!pending || !data} className="space-y-3">
        <label className="block">Referencia de visita<input className={field} required pattern={"[A-Za-z0-9_\\-]{1,80}"} maxLength={80} placeholder="Ejemplo: VISITA-001" autoCapitalize="none" autoCorrect="off" spellCheck={false} value={draft.visitor_ref} onChange={e => setDraft({ ...draft, visitor_ref: e.target.value })} /></label>
        <label className="block" htmlFor="visit-host">Anfitrión</label><select id="visit-host" className={field} required value={draft.host_user_id} onChange={e => setDraft({ ...draft, host_user_id: e.target.value })}>
          <option value="">Seleccionar anfitrión</option>{data?.caps.hosts.map(h => <option key={h.user_id} value={h.user_id}>{h.nombre}</option>)}</select>
        <label className="block" htmlFor="visit-destination">Destino</label><select id="visit-destination" className={field} required value={draft.destination_id} onChange={e => setDraft({ ...draft, destination_id: e.target.value })}>
          <option value="">Seleccionar destino</option>{data?.destinations.map(d => <option key={d.destination_id} value={d.destination_id}>{d.nombre}</option>)}</select>
      </fieldset>
      <button className={button} disabled={busy || (!data && !pending)}>{pending ? "Reintentar misma solicitud" : "Crear preregistro"}</button>
    </form> : null}
    {review && data ? <section role="dialog" aria-modal="false" aria-labelledby="visit-review" className="space-y-3 rounded-xl border border-blue-400 p-4">
      <h2 id="visit-review" className="text-xl font-semibold">Confirmar movimiento</h2>
      <p>{actions[review.action]}</p>
      <p className="break-all text-sm">Referencia: {review.visit.visitor_ref}</p>
      <button autoFocus className={button} disabled={busy} onClick={confirm}>Confirmar</button>{" "}
      <button className={button} disabled={busy} onClick={() => setReview(null)}>Volver</button>
    </section> : null}
    {data ? <section className="space-y-3"><h2 className="text-xl font-semibold">Últimas 50 visitas de esta sede</h2>
      {!data.visits.length ? <p>No hay visitas registradas.</p> : data.visits.map(v => <article key={v.visit_id} aria-label={`Visita con referencia ${v.visitor_ref}`} className="min-w-0 space-y-3 rounded-xl border border-gray-700 p-4">
        <h3 className="break-words text-lg font-semibold">Visita a {data.destinations.find(d => d.destination_id === v.destination_id)?.nombre || "destino no disponible"}</h3>
        <p className="inline-block rounded-full border border-gray-600 bg-gray-800 px-3 py-1 text-sm">{labels[v.state] || v.state}</p>
        <dl className="space-y-2 text-sm">
          <div><dt className="text-gray-400">Anfitrión</dt><dd className="break-words">{data.caps.hosts.find(h => h.user_id === v.host_user_id)?.nombre || "No disponible en el directorio"}</dd></div>
          <div><dt className="text-gray-400">Referencia de visita</dt><dd className="break-all font-mono">{v.visitor_ref}</dd></div>
        </dl>
        <div className="space-y-2 text-sm text-gray-300">
          <p>Entrada: <VisitTime value={v.entered_at} zone={data.site.zona_horaria} /></p>
          <p>Salida: <VisitTime value={v.exited_at} zone={data.site.zona_horaria} /></p>
        </div>
        <div className="flex flex-wrap gap-3">
          {[(data.caps.can_authorize && v.state === "preregistrada") ? "autorizar" : "",
            (data.caps.can_record_movement && v.state === "autorizada") ? "entrada" : "",
            (data.caps.can_record_movement && v.state === "dentro") ? "salida" : "",
            (data.caps.can_authorize && ["preregistrada", "autorizada"].includes(v.state)) ? "cancelar" : ""].filter(Boolean).map(action =>
            <button className={button} key={action} disabled={busy} onClick={() => setReview({ visit: v, action })}>{actions[action]}</button>)}
          <button className={`${button} w-full sm:w-auto`} disabled={busy} aria-expanded={log?.visitId === v.visit_id} aria-controls={`visit-log-${v.visit_id}`} onClick={() => openLog(v)}>{log?.visitId === v.visit_id ? "Cerrar bitácora" : "Ver bitácora"}</button>
        </div>
        {log?.visitId === v.visit_id ? <section id={`visit-log-${v.visit_id}`} className="space-y-3 border-t border-gray-700 pt-4" aria-label="Bitácora de visita">
          <h4 className="font-semibold">Bitácora de esta visita</h4>
          {!log.entries.length ? <p className="text-sm text-gray-300">No hay movimientos disponibles en la bitácora.</p> : <ol className="space-y-3">{log.entries.map(row => <li key={row.event_uid} className="border-l-2 border-blue-500 pl-3 text-sm">
            <p className="font-semibold">{events[row.action] || row.action}</p>
            <VisitTime value={row.timestamp} zone={data.site.zona_horaria} />
          </li>)}</ol>}
        </section> : null}
      </article>)}
    </section> : null}
  </>;
}
