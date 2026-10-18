"use client";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

export function VistaFotoSalida({ file }: { file: File }) {
  const image = useRef<HTMLImageElement>(null);
  useEffect(() => { const value = URL.createObjectURL(file); if (image.current) image.current.src = value; return () => URL.revokeObjectURL(value); }, [file]);
  // Private in-memory preview; no public optimizer or persistent browser storage.
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={image} alt="Foto seleccionada como evidencia de salida" className="max-h-64 rounded-lg object-contain" />;
}

export default function EvidenciaSalida({ visitaId, condominioId }: { visitaId: string; condominioId: string }) {
  const { getToken } = useAuth();
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  async function ver() {
    setBusy(true); setStatus("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Vuelve a iniciar sesión");
      const path = `/evidencias-salida/${encodeURIComponent(visitaId)}`;
      const scope = `?condominio_id=${encodeURIComponent(condominioId)}`;
      const rows = await api.get<{ evidencia_id: string }[]>(path + scope, token);
      if (!rows.length) { setStatus("Esta salida no tiene foto de evidencia."); return; }
      const blob = await api.download(`${path}/${encodeURIComponent(rows[0].evidencia_id)}${scope}`, token);
      setUrl(URL.createObjectURL(blob));
    } catch (e) { setStatus(e instanceof Error ? e.message : "No se pudo consultar la foto"); }
    finally { setBusy(false); }
  }
  return <div className="space-y-3">
    <button disabled={busy} onClick={ver} className="min-h-12 rounded-xl border border-gray-600 px-4 py-3">{busy ? "Cargando foto…" : "Ver evidencia de salida"}</button>
    {status && <p role="status">{status}</p>}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    {url && <img src={url} alt="Evidencia de salida guardada" className="max-h-96 rounded-lg object-contain" />}
  </div>;
}
