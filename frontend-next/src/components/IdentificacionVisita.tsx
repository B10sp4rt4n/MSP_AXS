"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Evidence = { evidencia_id: string; lado: string; nombre: string; created_at: string };
type Result = { evidencias: Evidence[] };

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

function Preview({ blob, label }: { blob: Blob; label: string }) {
  const imageRef = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const value = URL.createObjectURL(blob);
    if (imageRef.current) imageRef.current.src = value;
    return () => URL.revokeObjectURL(value);
  }, [blob]);
  // Object URLs are local previews, never public image URLs.
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={imageRef} alt={label} className="mt-2 max-h-64 w-full rounded-lg object-contain" />;
}

function SavedIdentityPhotos({ rows, path, query, getToken }: {
  rows: Evidence[]; path: string; query: string; getToken: () => Promise<string | null>;
}) {
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [states, setStates] = useState<Record<string, { blob?: Blob; error?: string }>>({});
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    const fail = (row: Evidence, error: unknown) => {
      if (!active) return;
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
  }, [rows, path, query, getToken, attempt]);

  return <div className="mt-4 space-y-3" aria-busy={loading}>
    {rows.map(row => {
      const side = row.lado === "ine_frente" ? "Frente" : "Reverso";
      const state = states[row.evidencia_id];
      return <div key={row.evidencia_id} className="rounded-xl border border-gray-700 p-3">
        <h3 className="font-semibold">{side} guardado</h3>
        {state?.blob ? <Preview blob={state.blob} label={`${side} guardado`} />
          : state?.error ? <p role="alert" className="mt-2 text-sm text-red-300">{state.error}</p>
          : <p role="status" className="mt-2 min-h-24 animate-pulse rounded-lg bg-gray-900 p-4 text-sm text-gray-300">Cargando foto del {side.toLowerCase()}…</p>}
      </div>;
    })}
    <button type="button" onClick={() => setAttempt(value => value + 1)} disabled={loading}
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
  const [captureId, setCaptureId] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    getToken().then(token => {
      if (!token) throw new Error("Sesión expirada");
      return api.get<Result>(path + query, token);
    }).then(result => {
      if (active) { setRows(result.evidencias); setReady(true); }
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : "No se pudo consultar"); });
    return () => { active = false; };
  }, [getToken, path, query, reload]);

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
      setRows(result.evidencias); setPhotos({}); setConfirmed(false);
    } catch (e) { setError(e instanceof Error ? e.message : "No se confirmó el guardado. Reintenta."); }
    finally { setBusy(false); }
  }

  return <div className="mt-3 rounded-xl border border-gray-700 bg-gray-950 p-3">
    {error && <p role="alert" className="mb-3 text-sm text-red-300">{error}</p>}
    {!ready && !error && <p role="status">Consultando identificación…</p>}
    {error && <button type="button" disabled={busy} className="mb-3 text-sm underline" onClick={() => { setReady(false); setError(""); setReload(v => v + 1); }}>Consultar estado guardado</button>}
    {rows.length > 0 ? <>
      <p role="status" className="font-semibold text-green-300">Frente y reverso guardados</p>
      <p className="mt-2">Nombre registrado: {rows[0].nombre}</p>
      <p className="text-xs text-gray-400">{new Date(rows[0].created_at).toLocaleString("es-MX")}</p>
      <SavedIdentityPhotos rows={rows} path={path} query={query} getToken={getToken} />
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
