"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Evidence = { evidencia_id: string; lado: string; nombre: string; created_at: string };
type Result = { evidencias: Evidence[] };

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

export default function IdentificacionVisita({ visitaId, condominioId, nombreInvitado }: {
  visitaId: string; condominioId: string; nombreInvitado: string;
}) {
  const { getToken } = useAuth();
  const uid = useId();
  const [open, setOpen] = useState(false);
  return <section className="mt-4 text-left">
    <button type="button" aria-expanded={open} aria-controls={uid} onClick={() => setOpen(!open)}
      className="w-full rounded-lg border border-gray-600 p-3 text-sm">
      {open ? "Cerrar identificación (descarta fotos sin guardar)" : "Identificación: fotos y nombre"}
    </button>
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
  const [savedPhotos, setSavedPhotos] = useState<Record<string, Blob>>({});
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

  async function viewPhotos() {
    setBusy(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sesión expirada");
      const loaded: Record<string, Blob> = {};
      for (const row of rows) loaded[row.evidencia_id] = await api.download(`${path}/${encodeURIComponent(row.evidencia_id)}${query}`, token);
      setSavedPhotos(loaded);
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudieron consultar las fotos"); }
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
      <button type="button" onClick={viewPhotos} disabled={busy} className="mt-3 rounded-lg bg-blue-700 px-4 py-2 disabled:opacity-50">{busy ? "Cargando…" : "Consultar fotos"}</button>
      {rows.map(row => savedPhotos[row.evidencia_id] && <Preview key={row.evidencia_id} blob={savedPhotos[row.evidencia_id]} label={row.lado === "ine_frente" ? "Frente guardado" : "Reverso guardado"} />)}
    </> : ready && <form onSubmit={save} className="space-y-4">
      <p className="text-sm text-gray-300">Coloca la identificación completa, con buena luz y sin reflejos. Revisa que ambos lados sean legibles.</p>
      <fieldset disabled={busy} className="space-y-4 disabled:opacity-60">
        {(["frente", "reverso"] as const).map(side => <div key={side}>
          <label htmlFor={`${uid}-${side}`} className="block text-sm font-semibold">{side === "frente" ? "1. Foto del frente" : "2. Foto del reverso"}</label>
          <input id={`${uid}-${side}`} type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
            className="mt-2 w-full text-sm" onChange={e => { select(side, e.target.files?.[0]); e.target.value = ""; }} />
          {photos[side] && <><Preview blob={photos[side]} label={`Vista previa del ${side}`} /><p className="text-xs text-gray-400">Para repetir, selecciona otra foto.</p></>}
        </div>)}
        <label htmlFor={`${uid}-nombre`} className="block text-sm">3. Nombre completo según identificación
          <input id={`${uid}-nombre`} required minLength={2} maxLength={200} value={nombre}
            onChange={e => { setNombre(e.target.value); setCaptureId(crypto.randomUUID()); setConfirmed(false); }}
            className="mt-2 w-full rounded-lg border border-gray-600 bg-gray-800 p-3" />
        </label>
        {nombre.trim() !== nombreInvitado.trim() && <p className="text-sm text-amber-300">Invitación: {nombreInvitado}. El nombre capturado se conserva por separado.</p>}
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Revisé el nombre y la legibilidad de ambas fotos.</label>
        <button disabled={!photos.frente || !photos.reverso || !confirmed || !nombre.trim()} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-40">{busy ? "Guardando ambas fotos…" : "Guardar identificación"}</button>
      </fieldset>
      <p className="text-xs text-gray-400">Las fotos pendientes se conservan solo mientras esta pantalla siga abierta. Este registro no autoriza la entrada.</p>
    </form>}
  </div>;
}
