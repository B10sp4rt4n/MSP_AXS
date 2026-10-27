"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { api, ApiError } from "@/lib/api";

type Site = { site_id: string; tenant_id: string; nombre: string; zona_horaria: string; activa: boolean };
type Destination = { destination_id: string; tenant_id: string; site_id: string; nombre: string; activa: boolean };
type TokenGetter = () => Promise<string | null>;
const inputClass = "w-full rounded-xl border border-gray-600 bg-gray-800 p-3 text-white focus-visible:outline-2 focus-visible:outline-blue-400";
const buttonClass = "min-h-12 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-500 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-blue-300";
const panelClass = "rounded-2xl border border-gray-700 bg-gray-900 p-5";
const companyPattern = /^corp_[a-zA-Z0-9_-]{1,100}$/;

function message(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Tu sesión venció. Vuelve a iniciar sesión.";
    if (error.status === 403) return "Tu cuenta no tiene permiso para esta operación o el directorio no está habilitado.";
    if (error.status === 404) return "Directorio o sede no disponible.";
    return error.message;
  }
  return "No pudimos confirmar la respuesta del servidor.";
}

export default function CorporateDirectoryClient({ initialTenant = "" }: { initialTenant?: string }) {
  const { userId, isLoaded, getToken } = useAuth();
  const [tenant, setTenant] = useState(companyPattern.test(initialTenant) ? initialTenant : "");
  const [candidate, setCandidate] = useState(initialTenant);
  const [invalid, setInvalid] = useState("");
  function open(event: FormEvent) {
    event.preventDefault();
    const value = candidate.trim();
    if (!companyPattern.test(value)) { setInvalid("Indica el identificador corporativo que te compartió el administrador."); return; }
    setInvalid(""); setTenant(value);
    const url = new URL(window.location.href);
    url.searchParams.set("empresa", value);
    window.history.replaceState(null, "", url);
  }
  return <div className="min-h-screen bg-gray-950 text-white">
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 p-5">
      <div><h1 className="text-2xl font-bold">AXS Corporativo · Directorio</h1>
        <p className="mt-1 text-sm text-gray-300">Organiza las sedes y los destinos de tu empresa.</p></div>
      <UserButton />
    </header>
    <main className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <form onSubmit={open} className={panelClass}>
        <label htmlFor="company" className="mb-2 block font-semibold">Identificador de empresa</label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input id="company" value={candidate} onChange={e => setCandidate(e.target.value)} className={inputClass} maxLength={105} required autoComplete="off" placeholder="corp_…" />
          <button className={`${buttonClass} shrink-0`} disabled={!isLoaded || !userId}>Abrir directorio</button>
        </div>
        <p className="mt-2 text-sm text-gray-400">El identificador selecciona la empresa; el servidor comprueba tus permisos.</p>
        {invalid ? <p role="alert" className="mt-3 text-red-300">{invalid}</p> : null}
      </form>
      {!isLoaded ? <p role="status">Comprobando sesión…</p> : !userId ? <p role="alert">Inicia sesión para consultar tu directorio.</p>
        : tenant ? <Directory key={`${userId}:${tenant}`} tenant={tenant} getToken={getToken} /> : null}
    </main>
  </div>;
}

function Directory({ tenant, getToken }: { tenant: string; getToken: TokenGetter }) {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [selected, setSelected] = useState("");
  const [destinations, setDestinations] = useState<Destination[] | null>(null);
  const [siteName, setSiteName] = useState("");
  const [timezone, setTimezone] = useState("America/Mexico_City");
  const [destinationName, setDestinationName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const lifetime = useRef<AbortController | null>(null);
  const mutationLock = useRef(false);
  const base = `/corporativo/${encodeURIComponent(tenant)}`;
  const selectedSite = sites?.find(site => site.site_id === selected);

  useEffect(() => {
    const controller = new AbortController();
    lifetime.current = controller;
    return () => { controller.abort(); };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        if (!token) throw new ApiError("Sin sesión", 401);
        const rows = await api.get<Site[]>(`${base}/sedes`, token, controller.signal);
        if (controller.signal.aborted) return;
        setSites(rows);
        setSelected(previous => rows.some(s => s.site_id === previous && s.activa) ? previous : "");
        setUncertain(false);
      } catch (err) {
        if (!controller.signal.aborted) setError(message(err));
      } finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [base, getToken, revision]);

  useEffect(() => {
    if (!selected || !sites) return;
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        if (!token) throw new ApiError("Sin sesión", 401);
        const rows = await api.get<Destination[]>(`${base}/sedes/${encodeURIComponent(selected)}/destinos`, token, controller.signal);
        if (!controller.signal.aborted) setDestinations(rows);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(message(err));
          if (err instanceof ApiError && [401, 403].includes(err.status)) setSites(null);
        }
      }
    })();
    return () => controller.abort();
  }, [base, getToken, selected, sites]);

  async function create(event: FormEvent, kind: "site" | "destination") {
    event.preventDefault();
    if (mutationLock.current || uncertain || !sites || (kind === "destination" && !destinations)) return;
    mutationLock.current = true;
    setBusy(true); setError(""); setNotice("");
    const signal = lifetime.current!.signal;
    try {
      const token = await getToken();
      if (!token) throw new ApiError("Sin sesión", 401);
      if (signal.aborted) return;
      if (kind === "site") {
        const row = await api.post<Site>(`${base}/sedes`, { nombre: siteName.trim(), zona_horaria: timezone.trim() }, token, signal);
        if (signal.aborted) return;
        setSiteName(""); setSites(previous => [...(previous ?? []), row]);
        setSelected(row.site_id); setDestinations(null); setDestinationName("");
        setNotice(`Sede creada: ${row.nombre}`);
      } else {
        const row = await api.post<Destination>(`${base}/sedes/${encodeURIComponent(selected)}/destinos`, { nombre: destinationName.trim() }, token, signal);
        if (signal.aborted) return;
        setDestinations(previous => [...(previous ?? []), row]); setDestinationName("");
        setNotice(`Destino creado: ${row.nombre}`);
      }
    } catch (err) {
      if (signal.aborted) return;
      setError(message(err));
      // POSTs are not idempotent. Never retry automatically after an unknown result.
      if (!(err instanceof ApiError) || err.status >= 500) setUncertain(true);
      if (err instanceof ApiError && [401, 403].includes(err.status)) { setSites(null); setDestinations(null); }
    } finally {
      mutationLock.current = false;
      if (!signal.aborted) setBusy(false);
    }
  }

  return <>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="min-w-0 break-all text-sm text-gray-400">Empresa: {tenant}</p>
      <button type="button" disabled={busy || loading} onClick={() => { setNotice(""); setError(""); setSites(null); setDestinations(null); setLoading(true); setRevision(v => v + 1); }} className="min-h-12 rounded-xl border border-gray-600 px-4 py-3 disabled:opacity-50">Consultar estado del directorio</button>
    </div>
    {error ? <p role="alert" className="rounded-xl border border-red-700 bg-red-950 p-4 text-red-200">{error}</p> : null}
    {uncertain ? <p role="alert" className="rounded-xl border border-yellow-700 bg-yellow-950 p-4 text-yellow-200">El alta pudo haberse guardado. Pulsa «Consultar estado del directorio» y revisa la lista antes de intentar otra alta.</p> : null}
    {notice ? <p role="status" className="rounded-xl border border-green-700 bg-green-950 p-4 text-green-200">{notice}</p> : null}
    {loading ? <p role="status">Comprobando acceso al directorio…</p> : null}
    {sites ? <div className="grid gap-5 md:grid-cols-2">
      <section className={panelClass} aria-labelledby="sites-title">
        <h2 id="sites-title" className="text-xl font-semibold">1. Sedes</h2>
        <p className="mt-1 text-sm text-gray-300">Una oficina, sucursal o edificio de tu empresa.</p>
        {sites.filter(s => s.activa).length === 0 ? <p className="my-4 text-gray-300">Todavía no hay sedes. Crea la primera.</p> : null}
        <div className="my-4 flex flex-col gap-3">{sites.filter(s => s.activa).map(site => <button key={site.site_id} type="button" disabled={busy || uncertain} aria-pressed={selected === site.site_id} onClick={() => { if (selected === site.site_id) return; setSelected(site.site_id); setDestinations(null); setDestinationName(""); setError(""); setNotice(""); }} className={`min-h-16 rounded-xl border p-4 text-left break-words disabled:opacity-50 ${selected === site.site_id ? "border-blue-400 bg-blue-950" : "border-gray-600 bg-gray-800"}`}>
          <span className="block font-semibold">{site.nombre}</span><span className="text-sm text-gray-300">{site.zona_horaria}</span>
        </button>)}</div>
        <form onSubmit={event => create(event, "site")} className="space-y-3 border-t border-gray-700 pt-4">
          <h3 className="font-semibold">Nueva sede</h3>
          <label className="block" htmlFor="site-name">Nombre de sede</label>
          <input id="site-name" className={inputClass} required minLength={2} maxLength={120} value={siteName} onChange={e => setSiteName(e.target.value)} disabled={busy || uncertain} />
          <label className="block" htmlFor="timezone">Zona horaria</label>
          <input id="timezone" className={inputClass} required minLength={3} maxLength={80} value={timezone} onChange={e => setTimezone(e.target.value)} disabled={busy || uncertain} />
          <button className={`${buttonClass} w-full`} disabled={busy || uncertain || siteName.trim().length < 2}>Crear sede</button>
        </form>
      </section>
      <section className={panelClass} aria-labelledby="destinations-title">
        <h2 id="destinations-title" className="text-xl font-semibold">2. Destinos</h2>
        {!selectedSite ? <p className="mt-4 text-gray-300">Selecciona una sede para ver sus destinos.</p> : <>
          <p className="mt-2 break-words font-semibold">Sede: {selectedSite.nombre}</p>
          <p className="mt-1 text-sm text-gray-300">Áreas como Recepción, Administración o Sala de juntas.</p>
          {destinations === null ? <p role="status" className="my-4">Consultando destinos…</p> : <>
            <ul className="my-4 space-y-3">{destinations.map(destination => <li key={destination.destination_id} className="break-words rounded-xl border border-gray-700 bg-gray-800 p-4">{destination.nombre}</li>)}</ul>
            {destinations.length === 0 ? <p className="my-4 text-gray-300">Esta sede todavía no tiene destinos.</p> : null}
            <form onSubmit={event => create(event, "destination")} className="space-y-3 border-t border-gray-700 pt-4">
              <h3 className="font-semibold">Nuevo destino</h3>
              <label className="block" htmlFor="destination-name">Nombre del destino</label>
              <input id="destination-name" className={inputClass} required minLength={2} maxLength={120} value={destinationName} onChange={e => setDestinationName(e.target.value)} disabled={busy || uncertain} />
              <button className={`${buttonClass} w-full`} disabled={busy || uncertain || destinationName.trim().length < 2}>Crear destino</button>
            </form>
          </>}
        </>}
      </section>
    </div> : null}
    <p className="text-sm text-gray-400">Las altas requieren ser propietario o administrador y respetan las capacidades contratadas. Este directorio no habilita visitas, QR ni accesos físicos.</p>
  </>;
}
