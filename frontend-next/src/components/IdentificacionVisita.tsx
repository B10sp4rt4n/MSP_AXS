"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ApiError } from "@/lib/api";

type Evidence = { evidencia_id: string; lado: string; nombre: string; created_at: string };
type Conservation = { estado: string; vencimiento_en: string; excepcion_hasta: string | null; requiere_atencion: boolean };
type Result = { evidencias: Evidence[]; estado?: "guardada" | "sin_identificacion" | "eliminando" | "eliminada" | "vencida" | "revision"; eliminada_en?: string | null; conservacion?: Conservation | null; puede_gestionar_conservacion?: boolean };

function PhotoCapture({ side, photo, onSelect }: {
  side: "frente" | "reverso"; photo?: File; onSelect: (file?: File) => void;
}) {
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const change = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSelect(e.target.files?.[0]); e.target.value = "";
  };
  return <div className="rounded-xl border border-gray-600 bg-gray-900 p-4">
    <h3 className="text-base font-semibold">{side === "frente" ? "1. Frente de la identificación" : "2. Reverso de la identificación"}</h3>
    <p className="mt-1 text-sm text-gray-300">{photo ? "Foto lista. Puedes repetirla antes de guardar." : "Toma una foto o elige una que ya tengas."}</p>
    <input ref={camera} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden onChange={change} aria-label={`Cámara del ${side}`} />
    <input ref={gallery} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={change} aria-label={`Archivo del ${side}`} />
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      <button type="button" onClick={() => camera.current?.click()} className="min-h-12 rounded-lg bg-blue-600 px-3 py-3 font-semibold hover:bg-blue-500">{photo ? `Repetir foto del ${side}` : `Tomar foto del ${side}`}</button>
      <button type="button" onClick={() => gallery.current?.click()} className="min-h-12 rounded-lg border border-gray-500 px-3 py-3 text-sm hover:bg-gray-800">{`Elegir archivo del ${side}`}</button>
    </div>
    {photo && <Preview blob={photo} label={`Vista previa del ${side}`} />}
  </div>;
}

function Preview({ blob, label, className, style }: {
  blob: Blob; label: string; className?: string; style?: React.CSSProperties;
}) {
  const imageRef = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const value = URL.createObjectURL(blob);
    if (imageRef.current) imageRef.current.src = value;
    return () => URL.revokeObjectURL(value);
  }, [blob]);
  // Object URLs are local previews, never public image URLs.
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={imageRef} alt={label} style={style} className={className ?? "mt-2 max-h-64 w-full rounded-lg object-contain"} />;
}

function PhotoViewer({ pictures, initialId, onClose }: {
  pictures: { id: string; side: string; blob: Blob }[]; initialId: string; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const [selectedId, setSelectedId] = useState(initialId);
  const [zoom, setZoom] = useState(1);
  const selected = pictures.find(picture => picture.id === selectedId) ?? pictures[0];
  useEffect(() => {
    const modal = dialog.current;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    modal?.showModal(); document.body.style.overflow = "hidden";
    return () => {
      modal?.close(); document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, []);
  function resetView(id?: string) {
    if (id) setSelectedId(id);
    setZoom(1); viewport.current?.scrollTo({ top: 0, left: 0 });
  }
  if (!selected) return null;
  return <dialog ref={dialog} aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }}
    className="fixed inset-0 m-auto h-[94dvh] max-h-none w-[96vw] max-w-5xl rounded-xl border border-gray-600 bg-gray-950 p-0 text-white backdrop:bg-black/80">
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-gray-700 p-3">
        <h2 id={titleId} className="font-semibold">Identificación · {selected.side}</h2>
        <button type="button" autoFocus onClick={onClose} className="min-h-12 rounded-lg border border-gray-500 px-3 text-sm">Cerrar y volver a la visita</button>
      </header>
      <div className="flex shrink-0 flex-wrap items-center gap-2 p-3">
        {pictures.map(picture => <button key={picture.id} type="button" aria-pressed={picture.id === selected.id}
          onClick={() => resetView(picture.id)} className={`min-h-12 rounded-lg px-4 ${picture.id === selected.id ? "bg-blue-600" : "border border-gray-500"}`}>{picture.side}</button>)}
        <button type="button" aria-label="Alejar foto" disabled={zoom <= 1} onClick={() => setZoom(value => Math.max(1, value - .5))}
          className="min-h-12 min-w-12 rounded-lg border border-gray-500 text-xl disabled:opacity-40">−</button>
        <output aria-live="polite" aria-label="Nivel de zoom" className="min-w-14 text-center text-sm">{Math.round(zoom * 100)}%</output>
        <button type="button" aria-label="Acercar foto" disabled={zoom >= 4} onClick={() => setZoom(value => Math.min(4, value + .5))}
          className="min-h-12 min-w-12 rounded-lg border border-gray-500 text-xl disabled:opacity-40">+</button>
        <button type="button" onClick={() => resetView()} className="min-h-12 rounded-lg border border-gray-500 px-3 text-sm">Ajustar foto</button>
      </div>
      <p className="shrink-0 px-3 pb-2 text-sm text-gray-300">Usa + para acercar. Desliza la imagen para recorrerla.</p>
      <div ref={viewport} className="min-h-0 flex-1 overflow-auto overscroll-contain bg-black p-2">
        <Preview key={selected.id} blob={selected.blob} label={`${selected.side} ampliado`} className="block h-auto rounded-lg"
          style={{ width: `${zoom * 100}%`, maxWidth: "none" }} />
      </div>
    </div>
  </dialog>;
}

function SavedIdentityPhotos({ rows, path, query, getToken, onWithdraw }: {
  rows: Evidence[]; path: string; query: string; getToken: () => Promise<string | null>; onWithdraw: () => void;
}) {
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [states, setStates] = useState<Record<string, { blob?: Blob; error?: string }>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    const fail = (row: Evidence, error: unknown) => {
      if (!active) return;
      if (error instanceof ApiError && error.status === 410) { active = false; controller.abort(); onWithdraw(); return; }
      const message = controller.signal.aborted ? "La carga tardó demasiado. Vuelve a intentarlo."
        : error instanceof Error ? error.message : "No se pudo cargar esta foto.";
      setStates(previous => ({ ...previous, [row.evidencia_id]: { error: message } }));
    };
    setLoading(true); setStates({});
    async function load() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Sesión expirada; vuelve a iniciar sesión");
        await Promise.all(rows.map(async row => {
          try {
            const blob = await api.download(`${path}/${encodeURIComponent(row.evidencia_id)}${query}`, token, controller.signal);
            if (active) setStates(previous => ({ ...previous, [row.evidencia_id]: { blob } }));
          } catch (error) { fail(row, error); }
        }));
      } catch (error) { rows.forEach(row => fail(row, error)); }
      finally { clearTimeout(timeout); if (active) setLoading(false); }
    }
    void load();
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [rows, path, query, getToken, attempt, onWithdraw]);

  return <div className="mt-4 space-y-3" aria-busy={loading}>
    <p className="text-sm text-gray-300">Toca una foto para ampliarla y leer los detalles.</p>
    <div className="grid grid-cols-2 gap-3">
    {rows.map(row => {
      const side = row.lado === "ine_frente" ? "Frente" : "Reverso";
      const state = states[row.evidencia_id];
      return <div key={row.evidencia_id} className="rounded-xl border border-gray-700 p-3">
        <h3 className="font-semibold">{side} guardado</h3>
        {state?.blob ? <button type="button" onClick={() => setSelectedId(row.evidencia_id)} aria-label={`Ampliar ${side.toLowerCase()}`}
          className="mt-2 w-full rounded-lg text-left focus-visible:outline-2 focus-visible:outline-blue-400">
          <Preview blob={state.blob} label={`${side} guardado`} className="h-32 w-full rounded-lg bg-black object-contain sm:h-40" />
          <span className="mt-2 block text-center text-sm text-blue-300">Ampliar {side.toLowerCase()}</span>
        </button>
          : state?.error ? <p role="alert" className="mt-2 text-sm text-red-300">{state.error}</p>
          : <p role="status" className="mt-2 min-h-24 animate-pulse rounded-lg bg-gray-900 p-4 text-sm text-gray-300">Cargando foto del {side.toLowerCase()}…</p>}
      </div>;
    })}
    </div>
    {selectedId && states[selectedId]?.blob && <PhotoViewer initialId={selectedId} onClose={() => setSelectedId(null)}
      pictures={rows.flatMap(row => { const blob = states[row.evidencia_id]?.blob; return blob ? [{ id: row.evidencia_id, side: row.lado === "ine_frente" ? "Frente" : "Reverso", blob }] : []; })} />}
    <button type="button" onClick={() => { setSelectedId(null); setAttempt(value => value + 1); }} disabled={loading}
      className="min-h-12 rounded-lg border border-gray-500 px-4 py-2 disabled:opacity-50">
      {loading ? "Cargando fotos…" : "Volver a cargar fotos"}
    </button>
  </div>;
}

export default function IdentificacionVisita({ visitaId, condominioId, nombreInvitado }: {
  visitaId: string; condominioId: string; nombreInvitado: string;
}) {
  const { getToken } = useAuth();
  const uid = useId();
  const [open, setOpen] = useState(false);
  return <section className="mt-4 text-left">
    <button type="button" aria-expanded={open} aria-controls={uid} onClick={() => setOpen(!open)}
      className={`min-h-12 w-full rounded-lg p-3 text-base font-semibold ${open ? "border border-gray-600" : "bg-blue-600 text-white hover:bg-blue-500"}`}>
      {open ? "Cerrar identificación" : "Capturar o ver identificación"}
    </button>
    {!open && <p className="mt-2 text-sm text-gray-300">Abre aquí para tomar las fotos del frente y reverso, o consultar las guardadas.</p>}
    {open && <div id={uid}><IdentityForm key={`${condominioId}:${visitaId}`} visitaId={visitaId}
      condominioId={condominioId} nombreInvitado={nombreInvitado} getToken={getToken} /></div>}
  </section>;
}

function IdentityForm({ visitaId, condominioId, nombreInvitado, getToken }: {
  visitaId: string; condominioId: string; nombreInvitado: string;
  getToken: () => Promise<string | null>;
}) {
  const uid = useId();
  const path = `/identificaciones/${encodeURIComponent(visitaId)}`;
  const query = `?condominio_id=${encodeURIComponent(condominioId)}`;
  const [nombre, setNombre] = useState(nombreInvitado);
  const [photos, setPhotos] = useState<{ frente?: File; reverso?: File }>({});
  const [rows, setRows] = useState<Evidence[]>([]);
  const [identityStatus, setIdentityStatus] = useState<Result["estado"]>();
  const [conservation, setConservation] = useState<Conservation | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [captureId, setCaptureId] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [reload, setReload] = useState(0);
  const withdraw = useCallback(() => { setRows([]); setPhotos({}); setIdentityStatus("vencida"); setReload(value => value + 1); }, []);
  useEffect(() => {
    let active = true;
    getToken().then(token => {
      if (!token) throw new Error("Sesión expirada");
      return api.get<Result>(path + query, token);
    }).then(result => {
      if (active) { setRows(result.evidencias); setIdentityStatus(result.estado); setConservation(result.conservacion ?? null); setCanManage(!!result.puede_gestionar_conservacion); setReady(true); }
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : "No se pudo consultar"); });
    return () => { active = false; };
  }, [getToken, path, query, reload]);

  useEffect(() => {
    if (!conservation || !["vigente", "excepcion"].includes(conservation.estado)) return;
    const deadline = Math.max(new Date(conservation.vencimiento_en).getTime(), conservation.excepcion_hasta ? new Date(conservation.excepcion_hasta).getTime() : 0);
    const refresh = () => { setRows([]); setPhotos({}); setReady(false); setReload(value => value + 1); };
    const timer = setTimeout(refresh, Math.max(0, Math.min(deadline - Date.now(), 2147483647)));
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", visible);
    return () => { clearTimeout(timer); document.removeEventListener("visibilitychange", visible); };
  }, [conservation]);

  function select(side: "frente" | "reverso", file?: File) {
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
      setError("Usa JPEG, PNG o WebP de hasta 8 MB. Si es HEIC, cambia la cámara a formato compatible."); return;
    }
    setPhotos(p => ({ ...p, [side]: file }));
    setCaptureId(crypto.randomUUID()); setConfirmed(false); setError("");
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !photos.frente || !photos.reverso || !confirmed) return;
    setBusy(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sesión expirada; vuelve a iniciar sesión");
      const form = new FormData();
      form.append("nombre", nombre.trim()); form.append("captura_id", captureId);
      form.append("frente", photos.frente); form.append("reverso", photos.reverso);
      const result = await api.upload<Result>(path + query, form, token);
      setRows(result.evidencias); setIdentityStatus("guardada"); setPhotos({}); setConfirmed(false); setReload(value => value + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "No se confirmó el guardado. Reintenta."); }
    finally { setBusy(false); }
  }

  return <div className="mt-3 rounded-xl border border-gray-700 bg-gray-950 p-3">
    {error && <p role="alert" className="mb-3 text-sm text-red-300">{error}</p>}
    {!ready && !error && <p role="status">Consultando identificación…</p>}
    {error && <button type="button" disabled={busy} className="mb-3 text-sm underline" onClick={() => { setReady(false); setError(""); setReload(v => v + 1); }}>Consultar estado guardado</button>}
    {conservation && <div className="mb-3 rounded-lg border border-gray-700 p-3 text-sm">
      <p>Vencimiento: {new Date(conservation.vencimiento_en).toLocaleString("es-MX", { timeZone: "America/Mexico_City" })} · Ciudad de México</p>
      {conservation.excepcion_hasta && <p className="mt-1 text-amber-300">Conservación por incidencia hasta {new Date(conservation.excepcion_hasta).toLocaleString("es-MX", { timeZone: "America/Mexico_City" })}.</p>}
      {conservation.requiere_atencion && <p className="mt-1 text-amber-300">Requiere revisión del administrador.</p>}
      {canManage && <ConservationControls path={path} query={query} getToken={getToken} held={!!conservation.excepcion_hasta} onSaved={() => { setRows([]); setReady(false); setReload(value => value + 1); }} />}
    </div>}
    {identityStatus === "vencida" || identityStatus === "revision" ? <p role="status" className="text-sm text-amber-300">{identityStatus === "vencida" ? "La identificación alcanzó su plazo de conservación. Las fotos y el nombre transcrito ya no están disponibles para consulta." : "La identificación requiere revisión. Las fotos están retiradas de consulta."}</p>
    : identityStatus === "eliminada" ? <p role="status" className="text-sm text-gray-300">Identificación eliminada. La bitácora conserva el registro de la operación; las fotos ya no están disponibles.</p>
    : identityStatus === "eliminando" ? <div><p role="status" className="text-sm text-amber-300">Eliminación pendiente de completar. Las fotos están retiradas de consulta.</p><button type="button" onClick={() => { setReady(false); setReload(value => value + 1); }} className="mt-3 min-h-12 rounded-lg border border-gray-500 px-3">Actualizar estado</button></div>
    : rows.length > 0 ? <>
      <p role="status" className="font-semibold text-green-300">Frente y reverso guardados</p>
      <p className="mt-2">Nombre registrado: {rows[0].nombre}</p>
      <p className="text-xs text-gray-400">{new Date(rows[0].created_at).toLocaleString("es-MX")}</p>
      <SavedIdentityPhotos rows={rows} path={path} query={query} getToken={getToken} onWithdraw={withdraw} />
    </> : ready && <form onSubmit={save} className="space-y-4">
      <h2 className="text-lg font-semibold">Capturar identificación de {nombreInvitado}</h2>
      <p className="text-sm text-gray-300">Toma el frente, después el reverso y confirma el nombre. En celular se abre la cámara; en computadora puedes elegir archivos. Usa buena luz y evita reflejos.</p>
      <fieldset disabled={busy} className="space-y-4 disabled:opacity-60">
        <p role="status" className="text-sm font-semibold text-blue-200">{Number(!!photos.frente) + Number(!!photos.reverso)} de 2 fotos listas</p>
        {(["frente", "reverso"] as const).map(side => <PhotoCapture key={side} side={side} photo={photos[side]} onSelect={file => select(side, file)} />)}
        <label htmlFor={`${uid}-nombre`} className="block text-sm">3. Nombre completo según identificación
          <input id={`${uid}-nombre`} required minLength={2} maxLength={200} value={nombre}
            onChange={e => { setNombre(e.target.value); setCaptureId(crypto.randomUUID()); setConfirmed(false); }}
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-800 p-3" />
        </label>
        {nombre.trim() !== nombreInvitado.trim() && <p className="text-sm text-amber-300">Invitación: {nombreInvitado}. El nombre capturado se conserva por separado.</p>}
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Revisé el nombre y la legibilidad de ambas fotos.</label>
        <p className="text-sm text-gray-300">{!photos.frente ? "Falta tomar la foto del frente." : !photos.reverso ? "Falta tomar la foto del reverso." : !nombre.trim() ? "Escribe el nombre completo." : !confirmed ? "Marca la revisión del nombre y las dos fotos para guardar." : "Todo listo para guardar ambas fotos."}</p>
        <button disabled={!photos.frente || !photos.reverso || !confirmed || !nombre.trim()} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-40">{busy ? "Guardando ambas fotos…" : "Guardar identificación"}</button>
      </fieldset>
      <p className="text-xs text-gray-400">Las fotos pendientes se conservan solo mientras esta pantalla siga abierta. Este registro no autoriza la entrada.</p>
    </form>}
  </div>;
}

function ConservationControls({ path, query, getToken, held, onSaved }: {
  path: string; query: string; getToken: () => Promise<string | null>; held: boolean; onSaved: () => void;
}) {
  const uid = useId();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function change(form?: HTMLFormElement) {
    setBusy(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sesión expirada");
      const route = `${path}/conservacion/excepcion${query}`;
      if (form) {
        const data = new FormData(form);
        const date = new Date(String(data.get("hasta")));
        if (!Number.isFinite(date.getTime()) || date <= new Date()) throw new Error("Selecciona una fecha límite futura.");
        await api.put(route, { hasta: date.toISOString(), responsable: data.get("responsable"), incidencia: data.get("incidencia"), motivo: data.get("motivo") }, token);
      } else await api.delete(route, token);
      onSaved();
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo actualizar la conservación."); }
    finally { setBusy(false); }
  }
  return <details className="mt-3">
    <summary className="cursor-pointer py-2 text-blue-300">Conservar por una incidencia</summary>
    <p className="mb-3 text-gray-300">Indica quién se responsabiliza y cuándo termina la excepción. La fecha usa la hora de este dispositivo; el resultado se muestra en hora de Ciudad de México.</p>
    {error && <p role="alert" className="mb-2 text-red-300">{error}</p>}
    <form onSubmit={event => { event.preventDefault(); void change(event.currentTarget); }}>
      <fieldset disabled={busy} className="grid gap-3 disabled:opacity-50">
        {([{ name: "responsable", label: "Responsable", max: 200 }, { name: "incidencia", label: "Referencia de incidencia", max: 100 }, { name: "motivo", label: "Motivo de conservación", max: 500 }] as const).map(field => <label key={field.name} htmlFor={`${uid}-${field.name}`}>{field.label}<input id={`${uid}-${field.name}`} name={field.name} required maxLength={field.max} className="mt-1 w-full rounded-lg border border-gray-600 bg-gray-800 p-3" /></label>)}
        <label htmlFor={`${uid}-hasta`}>Fecha y hora límite<input id={`${uid}-hasta`} type="datetime-local" name="hasta" required className="mt-1 w-full rounded-lg border border-gray-600 bg-gray-800 p-3" /></label>
        <button className="min-h-12 rounded-lg bg-blue-600 px-3">{busy ? "Guardando…" : "Guardar excepción"}</button>
        {held && <button type="button" onClick={() => void change()} className="min-h-12 rounded-lg border border-gray-500 px-3">Terminar excepción</button>}
      </fieldset>
    </form>
  </details>;
}
