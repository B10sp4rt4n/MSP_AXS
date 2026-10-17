"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ApiError } from "@/lib/api";
import type { Visita } from "@/lib/types";

// Same dimensions as the existing guard controls.
const button = "min-h-12 rounded-xl border border-gray-600 px-4 py-3 font-semibold hover:bg-gray-800 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-purple-400";
const input = "min-h-12 w-full rounded-xl border border-gray-600 bg-gray-900 px-4";
type Solicitud = {
  solicitud_id: string; visita_id: string; destino_id: string; casa_unidad: string;
  nombre_visitante: string; proposito: string; expira_en: string;
  estado: "pendiente" | "permitida" | "rechazada" | "expirada" | "consumida";
  entrada_registrada: boolean;
};
const mensajes = {
  pendiente: "Esperando la decisión del residente. Aún no permitas la entrada.",
  permitida: "El residente permitió el acceso. Falta confirmar la entrada en caseta.",
  rechazada: "El residente rechazó el acceso. No permitas la entrada.",
  expirada: "La solicitud venció. No hay permiso vigente para entrar.",
  consumida: "Entrada registrada en caseta.",
};
type Payload = { solicitud_id: string; destino_id: string; nombre_visitante: string; tipo_visita: string; proposito: string; visita_id?: string };

export default function SolicitudesAcceso({ condominioId, destinoId, visita, residente = false, onRevisar }: {
  condominioId: string; destinoId?: string; visita?: Visita; residente?: boolean;
  onRevisar?: (id: string) => void;
}) {
  const { getToken } = useAuth();
  const [rows, setRows] = useState<Solicitud[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fresh, setFresh] = useState(false);
  const [abierto, setAbierto] = useState(false);
  const [nombre, setNombre] = useState(visita?.nombre_visitante ?? "");
  const [proposito, setProposito] = useState(visita?.proposito ?? "");
  const [tipo, setTipo] = useState(visita?.tipo_visita ?? "visita_personal");
  const [pendiente, setPendiente] = useState<Payload | null>(null);
  const [decision, setDecision] = useState<{ row: Solicitud; valor: "permitida" | "rechazada" } | null>(null);
  const [now, setNow] = useState(0);
  const lock = useRef(false);
  const revision = useRef(0);
  const alive = useRef(true);
  const base = `/solicitudes-acceso/${encodeURIComponent(condominioId)}`;
  const token = useCallback(async () => {
    const value = await getToken();
    if (!value) throw new Error("Tu sesión terminó. Vuelve a iniciar sesión.");
    return value;
  }, [getToken]);
  const cargar = useCallback(async () => {
    const current = ++revision.current;
    const data = await api.get<Solicitud[]>(base, await token(), AbortSignal.timeout(15000));
    if (alive.current && revision.current === current) { setRows(data); setFresh(true); setNow(Date.now()); }
    return data;
  }, [base, token]);
  useEffect(() => {
    alive.current = true;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (!lock.current) {
        try { await cargar(); }
        catch { if (!stopped) { setFresh(false); setError("No pudimos consultar las solicitudes. Comprueba la conexión y actualiza antes de continuar."); } }
      }
      if (!stopped) timer = setTimeout(poll, 5000);
    };
    void poll();
    const clock = setInterval(() => setNow(Date.now()), 1000);
    return () => { stopped = true; alive.current = false; clearTimeout(timer); clearInterval(clock); };
  }, [cargar]);
  const actualizar = async () => {
    if (lock.current) return;
    lock.current = true; revision.current++; setBusy(true); setError("");
    try { await cargar(); }
    catch { if (alive.current) { setFresh(false); setError("Sin conexión. No repitas una decisión ni permitas la entrada hasta comprobar el estado."); } }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  };
  async function solicitar() {
    if (lock.current || !destinoId) return;
    lock.current = true; revision.current++; setBusy(true); setError("");
    const payload = pendiente ?? { solicitud_id: crypto.randomUUID(), destino_id: destinoId,
      nombre_visitante: nombre.trim(), tipo_visita: tipo, proposito: proposito.trim(),
      ...(visita ? { visita_id: visita.visita_id } : {}) };
    setPendiente(payload);
    try {
      // Reusing this exact ID/body is safe even when the first POST response was lost.
      const row = await api.post<Solicitud>(base, payload, await token(), AbortSignal.timeout(15000));
      if (alive.current) { setRows(old => [row, ...old.filter(r => r.solicitud_id !== row.solicitud_id)]); setPendiente(null); setAbierto(false); setFresh(true); setNow(Date.now()); }
      await cargar();
    } catch (e) {
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        if (alive.current) { setPendiente(null); setError(e.message); }
        return;
      }
      try {
        const row = await api.get<Solicitud>(`${base}/${payload.solicitud_id}`, await token(), AbortSignal.timeout(15000));
        if (alive.current) { setRows(old => [row, ...old.filter(r => r.solicitud_id !== row.solicitud_id)]); setPendiente(null); setAbierto(false); setFresh(true); setNow(Date.now()); }
      } catch {
        if (alive.current) { setFresh(false); setError(`${e instanceof Error ? e.message : "No se confirmó el envío"}. Puedes recuperar o reintentar la misma solicitud sin duplicarla.`); }
      }
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function responder() {
    if (!decision || lock.current || !fresh) return;
    lock.current = true; revision.current++; setBusy(true); setError("");
    try {
      await api.post(`${base}/${decision.row.solicitud_id}/respuesta`,
        { decision: decision.valor, consentimiento: true }, await token(), AbortSignal.timeout(15000));
      if (alive.current) setDecision(null);
      await cargar();
    } catch (e) {
      if (alive.current) { setDecision(null); setFresh(false); setError(`${e instanceof Error ? e.message : "No se confirmó la respuesta"}. Actualiza para comprobar qué quedó registrado antes de responder otra vez.`); }
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const visibles = rows.filter(r => (!destinoId || r.destino_id === destinoId) && (!visita || r.visita_id === visita.visita_id));
  const vigente = (r: Solicitud) => fresh && now > 0 && new Date(r.expira_en).getTime() > now;
  return <section aria-label="Solicitudes de acceso" className="space-y-3 rounded-xl border border-purple-700 p-4">
    <h2 className="text-lg font-semibold">{residente ? "Alguien te visita en caseta" : "Autorización del residente"}</h2>
    <p className="text-sm text-gray-300">{residente ? "Permite o rechaza el acceso desde aquí. Al confirmar, AXS guardará tu decisión. La entrada la registra caseta." : "El residente decide con su app abierta. Si no responde, no hay autorización."}</p>
    {error && <p role="alert" className="text-amber-200">{error}</p>}
    <button className={button} disabled={busy} onClick={actualizar}>Actualizar solicitudes</button>
    {visibles.slice(0, 15).map(row => {
      const estado = ["pendiente", "permitida"].includes(row.estado) && now > 0 && !vigente(row) && fresh ? "expirada" : row.estado;
      return <article key={row.solicitud_id} className="space-y-2 rounded-xl border border-gray-700 p-3">
        <p className="font-semibold">{row.nombre_visitante} · {row.casa_unidad}</p>
        <p>{row.proposito}</p>
        <p role="status">{fresh ? mensajes[estado] : "Estado sin comprobar. Actualiza antes de continuar."}</p>
        {residente && estado === "pendiente" && vigente(row) && <div className="flex flex-wrap gap-2">
          <button className={`${button} text-emerald-200`} disabled={busy} onClick={() => setDecision({ row, valor: "permitida" })}>Permitir entrada</button>
          <button className={`${button} text-red-200`} disabled={busy} onClick={() => setDecision({ row, valor: "rechazada" })}>Rechazar entrada</button>
        </div>}
        {!residente && estado === "permitida" && vigente(row) && <button className={button} disabled={busy} onClick={() => onRevisar?.(row.visita_id)}>Revisar para confirmar entrada</button>}
      </article>;
    })}
    {fresh && visibles.length === 0 && <p>No hay solicitudes para mostrar.</p>}
    {decision && <div role="group" aria-label="Confirmar decisión" className="rounded-xl border border-purple-400 p-4 space-y-3">
      <p>¿Confirmas {decision.valor === "permitida" ? "permitir" : "rechazar"} la entrada de <strong>{decision.row.nombre_visitante}</strong> a {decision.row.casa_unidad}?</p>
      <button className={button} disabled={busy || !vigente(decision.row)} onClick={responder}>Confirmar {decision.valor === "permitida" ? "permiso" : "rechazo"}</button>{" "}
      <button className={button} disabled={busy} onClick={() => setDecision(null)}>Volver</button>
    </div>}
    {!residente && destinoId && !visita?.qr_token && <>
      {!abierto ? <button className={button} disabled={busy} onClick={() => setAbierto(true)}>Solicitar autorización sin QR</button> : <form className="space-y-3" onSubmit={e => { e.preventDefault(); void solicitar(); }}>
        <p>Confirma el nombre completo y el motivo. AXS conserva la vivienda elegida.</p>
        <label className="block">Nombre completo del visitante<input required minLength={3} maxLength={150} className={input} value={nombre} disabled={busy || !!pendiente || !!visita} onChange={e => setNombre(e.target.value)} /></label>
        <label className="block">Motivo de la visita<input required minLength={3} maxLength={500} className={input} value={proposito} disabled={busy || !!pendiente || !!visita?.proposito} onChange={e => setProposito(e.target.value)} /></label>
        <label className="block">Tipo de visita<select className={input} value={tipo} disabled={busy || !!pendiente || !!visita} onChange={e => setTipo(e.target.value)}>
          <option value="visita_personal">Personal</option><option value="proveedor">Servicio</option><option value="entrega">Entrega</option><option value="eventual">Eventual</option><option value="frecuente">Frecuente</option>
        </select></label>
        <button className={button} disabled={busy}>{pendiente ? "Recuperar o reintentar solicitud" : "Pedir decisión al residente"}</button>
        {!pendiente && <button type="button" className={button} disabled={busy} onClick={() => setAbierto(false)}>Volver</button>}
      </form>}
    </>}
  </section>;
}
