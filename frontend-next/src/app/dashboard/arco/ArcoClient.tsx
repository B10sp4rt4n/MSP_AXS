"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

type Case = { case_id: string; subject_ref: string; owner_id: string; right: string; received_at: string; determination_due: string; execution_due: string | null; state: string; version: number; pending_actions: number; history: { state: string; reference: string; at: string; actor: string }[] };
type Tenant = { condominio_id: string; nombre: string };
const states = ["recibida", "verificada", "resuelta", "ejecutando", "cerrada"];
const style = "min-h-11 rounded-lg border border-gray-600 bg-gray-900 p-3 text-white";
const button = `${style} disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-purple-400`;
const display = (value: string) => new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleString("es-MX", { timeZone: "America/Mexico_City" });
const iso = (value: FormDataEntryValue | null) => new Date(String(value)).toISOString();

export default function ArcoClient() {
  const { getToken } = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenant, setTenant] = useState("");
  const [rows, setRows] = useState<Case[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<Case | null>(null);
  const retry = useRef<{ fingerprint: string; id: string } | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    getToken().then(token => {
      if (!token) throw new Error("Inicia sesión nuevamente");
      return api.get<Tenant[]>("/condominios/", token, controller.signal);
    }).then(data => { if (!controller.signal.aborted) setTenants(data); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [getToken]);

  useEffect(() => {
    if (!tenant) return;
    const controller = new AbortController();
    getToken().then(token => {
      if (!token) throw new Error("Inicia sesión nuevamente");
      return api.get<Case[]>(`/arco/${encodeURIComponent(tenant)}?offset=${offset}&limit=20`, token, controller.signal);
    }).then(data => { if (!controller.signal.aborted) setRows(data); })
      .catch(e => { if (!controller.signal.aborted) {
        setRows(null);
        setError(e instanceof ApiError && e.status === 404 ? "El registro ARCO no está habilitado para operar. El canal público de privacidad sigue disponible." : e.message);
      } });
    return () => controller.abort();
  }, [tenant, offset, reload, getToken]);

  async function save(event: React.FormEvent<HTMLFormElement>, row?: Case) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity() || busy) return;
    const data = new FormData(form);
    const currentGeneration = generation.current;
    setBusy(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Inicia sesión nuevamente");
      const base = `/arco/${encodeURIComponent(tenant)}`;
      if (row) {
        const next = states[states.indexOf(row.state) + 1];
        const body: Record<string, unknown> = { version: row.version, state: next, reference: data.get("reference"), pending_actions: Number(data.get("pending_actions") || 0) };
        if (data.get("communication_ref")) body.communication_ref = data.get("communication_ref");
        if (next === "resuelta") {
          body.outcome = data.get("outcome");
          if (data.get("execution_due")) body.execution_due = iso(data.get("execution_due"));
        }
        await api.post(`${base}/${row.case_id}/estado`, body, token);
      } else {
        const body = { subject_ref: data.get("subject_ref"), owner_id: data.get("owner_id"), right: data.get("right"), received_at: iso(data.get("received_at")), determination_due: iso(data.get("determination_due")) };
        const fingerprint = JSON.stringify({ tenant, ...body });
        if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, id: crypto.randomUUID() };
        await api.post(base, { ...body, request_id: retry.current.id }, token);
        retry.current = null;
      }
      if (currentGeneration === generation.current) {
        setSelected(null); setRows(null); setReload(v => v + 1); form.reset();
      }
    } catch (e) {
      if (currentGeneration === generation.current) {
        setError(`${e instanceof Error ? e.message : "No se pudo guardar"}. Revisa el registro antes de reintentar.`);
        // A lost response may have committed. Refresh rather than blindly repeat a transition.
        setSelected(null); setRows(null); setReload(v => v + 1);
      }
    } finally { setBusy(false); }
  }

  return <main className="mx-auto min-h-screen max-w-4xl space-y-6 bg-gray-950 p-6 text-gray-100">
    <Link href="/dashboard/configuracion" className="underline">Volver a Configuración</Link>
    <h1 className="text-2xl font-semibold">Solicitudes ARCO</h1>
    <p>Registro privado para el personal de privacidad designado. Usa referencias del expediente seguro; no captures nombres, fotografías, contraseñas ni documentos aquí.</p>
    <p className="text-sm text-gray-400">Las fechas de recepción y vencimiento se capturan en la zona horaria de tu dispositivo. El historial se muestra en horario de Ciudad de México. Los plazos deben revisarse con el calendario aplicable.</p>
    <label className="grid gap-2">Cliente
      <select aria-label="Cliente" className={style} disabled={busy} value={tenant} onChange={e => {
        generation.current++; setTenant(e.target.value); setRows(null); setSelected(null); setOffset(0); setError(""); retry.current = null;
      }}><option value="">Selecciona un cliente</option>{tenants.map(t => <option key={t.condominio_id} value={t.condominio_id}>{t.nombre}</option>)}</select>
    </label>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {tenant && rows === null && !error && <p role="status">Consultando permisos y expedientes…</p>}
    {tenant && <button className={button} disabled={busy} onClick={() => { setRows(null); setSelected(null); setError(""); setReload(v => v + 1); }}>Actualizar</button>}
    {rows !== null && <>
      <section className="space-y-4 rounded-xl border border-gray-700 p-5">
        <h2 className="text-xl font-semibold">Registrar solicitud recibida</h2>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={e => save(e)}>
          <label className="grid gap-1">Referencia privada del titular<input required name="subject_ref" maxLength={100} pattern="[A-Za-z0-9_-]+" className={style}/></label>
          <label className="grid gap-1">Responsable asignado<input required name="owner_id" maxLength={100} className={style}/></label>
          <label className="grid gap-1">Derecho<select name="right" className={style}>{["acceso", "rectificacion", "cancelacion", "oposicion"].map(r => <option key={r}>{r}</option>)}</select></label>
          <label className="grid gap-1">Recepción original<input required type="datetime-local" name="received_at" className={style}/></label>
          <label className="grid gap-1">Vencimiento de determinación<input required type="datetime-local" name="determination_due" className={style}/></label>
          <button disabled={busy} className={button}>Registrar solicitud</button>
        </form>
      </section>
      <section className="space-y-3"><h2 className="text-xl font-semibold">Expedientes</h2>
        {rows.length === 0 && <p>No hay expedientes en esta página.</p>}
        {rows.map(row => <article key={row.case_id} className="space-y-2 rounded-xl border border-gray-700 p-4">
          <p className="break-all font-medium">Folio: {row.case_id}</p>
          <p>{row.right} · {row.state} · Pendientes: {row.pending_actions}</p>
          <p>Responsable: {row.owner_id} · Titular: {row.subject_ref}</p>
          <p>Recibida: {display(row.received_at)} · Determinación: {display(row.determination_due)}</p>
          {row.execution_due && <p>Ejecución: {display(row.execution_due)}</p>}
          <button className={button} disabled={busy} onClick={() => setSelected(row)}>Ver seguimiento</button>
        </article>)}
        <div className="flex gap-3"><button className={button} disabled={busy || offset === 0} onClick={() => { setRows(null); setSelected(null); setOffset(v => Math.max(0, v - 20)); }}>Anterior</button><button className={button} disabled={busy || rows.length < 20} onClick={() => { setRows(null); setSelected(null); setOffset(v => v + 20); }}>Siguiente</button></div>
      </section>
      {selected && <section className="space-y-3 rounded-xl border border-purple-600 p-5" aria-label="Seguimiento del expediente">
        <h2 className="break-all text-xl">Seguimiento: {selected.case_id}</h2>
        <ol>{selected.history.map((entry, i) => <li key={i}>{display(entry.at)} · {entry.state} · Referencia: {entry.reference} · Operador: {entry.actor}</li>)}</ol>
        {selected.state !== "cerrada" && <form key={`${selected.case_id}-${selected.version}`} className="grid gap-4" onSubmit={e => save(e, selected)}>
          <p>Siguiente estado: {states[states.indexOf(selected.state) + 1]}</p>
          <label className="grid gap-1">Referencia de evidencia<input required name="reference" pattern="[A-Za-z0-9_-]+" maxLength={100} className={style}/></label>
          {selected.state === "verificada" && <>
            <label className="grid gap-1">Decisión<select name="outcome" className={style}><option value="procedente">Procedente</option><option value="parcial">Parcial</option><option value="improcedente">Improcedente</option></select></label>
            <label className="grid gap-1">Vencimiento de ejecución (si procede)<input type="datetime-local" name="execution_due" className={style}/></label>
          </>}
          <label className="grid gap-1">Acciones pendientes<input type="number" name="pending_actions" min={0} max={10000} defaultValue={selected.pending_actions} className={style}/></label>
          <label className="grid gap-1">Constancia de comunicación{["verificada", "ejecutando"].includes(selected.state) ? " (obligatoria)" : " (opcional)"}<input required={["verificada", "ejecutando"].includes(selected.state)} name="communication_ref" pattern="[A-Za-z0-9_-]+" maxLength={100} className={style}/></label>
          <p className="text-sm text-gray-400">Registrar avances no envía respuestas ni ejecuta eliminaciones. Confirma la evidencia antes de guardar.</p>
          <button disabled={busy} className={button}>Confirmar avance</button>
        </form>}
      </section>}
    </>}
  </main>;
}
