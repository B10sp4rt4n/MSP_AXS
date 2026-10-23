"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type MSP = { msp_id: string; nombre: string };
type State = { autorizado: boolean; credencial_configurada: boolean; alcance: string };
type Owner = { usuario_id: string; nombre: string; email: string };
type Capacidades = { max_sedes: number | null; max_destinos_por_sede: number | null };
type Company = {
  tenant_id: string; nombre: string; msp_id: string; owner_user_id: string;
  modalidad: "corporativo"; directorio_habilitado: boolean;
  privacy_notice_version: string; privacy_contact: string;
  privacy_notice_url?: string; capacidades?: Capacidades;
};
type Form = {
  nombre: string; msp_id: string; owner_user_id: string;
  privacy_contact: string; privacy_notice_url: string; privacy_notice_version: string;
};
type Pending = { kind: "create" | "limits" | "activate"; detail: string; payload: Record<string, unknown> };
const base = "/plataforma/corporativo";
const field = "mt-1 block min-h-11 w-full rounded-lg border border-gray-600 bg-gray-900 p-3 text-white";
const primary = "min-h-11 rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-40";
const blank: Form = { nombre: "", msp_id: "", owner_user_id: "", privacy_contact: "", privacy_notice_url: "", privacy_notice_version: "" };

export default function CorporatePlatformClient() {
  const { userId } = useAuth();
  return <Console key={userId ?? "sin-sesion"} />;
}

function Console() {
  const { getToken } = useAuth();
  const [ready, setReady] = useState<State | null>(null);
  const [msps, setMsps] = useState<MSP[]>([]);
  const [form, setForm] = useState<Form>(blank);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [lookup, setLookup] = useState("");
  const [owner, setOwner] = useState<Owner | null>(null);
  const [limits, setLimits] = useState({ max_sedes: "2", max_destinos_por_sede: "10" });
  const [pending, setPending] = useState<Pending | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const lock = useRef(false);
  const confirmation = useRef<HTMLElement>(null);

  async function token() {
    const value = await getToken();
    if (!value) throw new Error("Sesión no disponible");
    return value;
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const auth = await token();
        const state = await api.get<State>(base + "/estado", auth);
        if (!state.autorizado) throw new Error("No autorizado");
        const providers = await api.get<MSP[]>("/msps/", auth);
        if (active) { setReady(state); setMsps(providers); setForm(f => ({ ...f, msp_id: f.msp_id || providers[0]?.msp_id || "" })); }
      } catch {
        if (active) setError("No se pudo verificar autoridad o cargar proveedores. No se habilitan operaciones.");
      } finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [getToken]);

  useEffect(() => {
    if (pending) {
      confirmation.current?.scrollIntoView({ block: "start", behavior: "instant" });
      confirmation.current?.focus({ preventScroll: true });
    }
  }, [pending]);

  async function executeRead<T>(work: (auth: string) => Promise<T>): Promise<T | null> {
    if (lock.current || !ready) return null;
    lock.current = true; setBusy(true); setError(""); setMessage("");
    try { return await work(await token()); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo consultar"); return null; }
    finally { lock.current = false; setBusy(false); }
  }

  async function checkOwner() {
    setOwner(null);
    const id = form.owner_user_id.trim();
    if (!id) { setError("Indica el identificador del usuario AXS"); return; }
    const result = await executeRead(auth => api.get<Owner>(base + "/usuarios/" + encodeURIComponent(id), auth));
    if (result) setOwner(result);
  }

  async function loadCompany() {
    const id = lookup.trim();
    if (!/^corp_[0-9a-f]{32}$/.test(id)) { setError("Indica un identificador corporativo válido"); return; }
    setPending(null); setCompany(null); setRequestId(null); setOwner(null);
    const result = await executeRead(auth => api.get<Company>(base + "/empresas/" + encodeURIComponent(id), auth));
    if (result) {
      setCompany(result);
      setLimits({
        max_sedes: String(result.capacidades?.max_sedes ?? 2),
        max_destinos_por_sede: String(result.capacidades?.max_destinos_por_sede ?? 10),
      });
    }
  }

  function prepareCreate() {
    if (!ready?.credencial_configurada || busy || pending) return;
    if (!form.nombre.trim() || !form.msp_id || !form.owner_user_id.trim() || !owner
      || owner.usuario_id !== form.owner_user_id.trim() || !form.privacy_contact.trim()
      || !form.privacy_notice_url.trim() || !form.privacy_notice_version.trim()) {
      setError("Completa todos los campos y verifica al administrador inicial."); return;
    }
    // El UUID persiste después de timeout/error hasta que el operador inicie otra alta.
    const id = requestId ?? crypto.randomUUID();
    setRequestId(id); setError(""); setMessage("");
    setPending({ kind: "create", detail: "Crear empresa deshabilitada y asignar el owner indicado.",
      payload: {
        request_id: id, nombre: form.nombre.trim(), msp_id: form.msp_id,
        owner_user_id: form.owner_user_id.trim(), privacy_contact: form.privacy_contact.trim(),
        privacy_notice_url: form.privacy_notice_url.trim(), privacy_notice_version: form.privacy_notice_version.trim(),
      } });
  }

  function prepareLimits() {
    if (!company || company.directorio_habilitado || busy || pending) return;
    const sedes = Number(limits.max_sedes), areas = Number(limits.max_destinos_por_sede);
    if (!Number.isInteger(sedes) || !Number.isInteger(areas) || sedes < 1 || sedes > 1000 || areas < 1 || areas > 2000) {
      setError("Límites inválidos: sedes 1–1000 y destinos por sede 1–2000."); return;
    }
    setPending({ kind: "limits", detail: "Configurar límites comerciales del directorio para esta empresa.",
      payload: { max_sedes: sedes, max_destinos_por_sede: areas } });
    setError(""); setMessage("");
  }

  function prepareActivation() {
    if (!company || company.directorio_habilitado || busy || pending) return;
    if (!company.capacidades?.max_sedes || !company.capacidades?.max_destinos_por_sede) {
      setError("Antes de habilitar, guarda las capacidades y consulta de nuevo la empresa."); return;
    }
    setPending({ kind: "activate", detail: "Habilitar exclusivamente el directorio. No habilita visitas, QR ni accesos físicos.",
      payload: { confirmacion: true } });
    setError(""); setMessage("");
  }

  async function execute() {
    if (!pending || lock.current || !ready?.credencial_configurada) return;
    const op = pending, selected = company?.tenant_id;
    if (op.kind !== "create" && !selected) return;
    lock.current = true; setBusy(true); setError(""); setMessage("");
    try {
      const auth = await token();
      if (op.kind === "create") {
        const created = await api.post<Company>(base + "/empresas", op.payload, auth);
        setCompany(created); setLookup(created.tenant_id); setPending(null);
        setMessage("Empresa registrada sin habilitar. Conserva el identificador para retomar la configuración.");
      } else if (op.kind === "limits") {
        await api.put(base + "/empresas/" + encodeURIComponent(selected!) + "/capacidades", op.payload, auth);
        setPending(null); setCompany(null);
        setMessage("Solicitud de capacidades recibida. Consulta de nuevo la empresa para verificar el resultado antes de habilitar.");
      } else {
        await api.post(base + "/empresas/" + encodeURIComponent(selected!) + "/habilitar-directorio", op.payload, auth);
        setPending(null); setCompany(null);
        setMessage("Solicitud de habilitación recibida. Consulta de nuevo para verificar el estado confirmado.");
      }
    } catch (e) {
      setError((e instanceof Error ? e.message : "Resultado incierto")
        + ". Verifica el estado antes de cambiar datos; puedes reintentar esta misma operación.");
    } finally { lock.current = false; setBusy(false); }
  }

  function resetCompany() {
    if (busy || pending) return;
    setForm({ ...blank, msp_id: msps[0]?.msp_id ?? "" }); setCompany(null);
    setLookup(""); setOwner(null); setRequestId(null); setMessage(""); setError("");
  }

  const locked = loading || busy || !!pending || !ready?.credencial_configurada;
  const hasCompany = !!company;
  return <main className="min-h-screen bg-gray-950 text-white p-4 sm:p-6">
    <div className="mx-auto max-w-4xl space-y-6">
      <a href="/dashboard" className="text-blue-300 underline">← Inicio</a>
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">AXS Corporativo · Superadmin</h1>
        <p className="text-gray-300">Aprovisionamiento controlado: empresa, administrador, capacidades y directorio.</p>
        <p className="text-sm text-amber-200">Esta consola no habilita visitantes, QR, puertas ni un piloto corporativo con datos reales.</p>
      </header>
      {loading && <p role="status">Comprobando autoridad y configuración…</p>}
      {ready && !ready.credencial_configurada && <p role="alert" className="rounded border border-amber-700 p-3 text-amber-200">
        Falta habilitar la credencial segregada del backend. No se permite crear ni activar empresas.
      </p>}
      {error && <p role="alert" className="rounded border border-amber-700 p-3 text-amber-200">{error}</p>}
      {message && <p role="status" className="rounded border border-gray-700 p-3 text-gray-200">{message}</p>}
      {ready && <>
        <section className="rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-4">
          <h2 className="text-lg font-semibold">1. Empresa y administrador inicial</h2>
          <p className="text-sm text-gray-300">El administrador ya debe existir en AXS. La empresa se crea inicialmente deshabilitada.</p>
          <fieldset disabled={locked || hasCompany || !!requestId} className="grid gap-3 sm:grid-cols-2 disabled:opacity-60">
            <label className="block sm:col-span-2">Nombre de empresa
              <input className={field} value={form.nombre} maxLength={120}
                onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} />
            </label>
            <label className="block">Proveedor MSP
              <select className={field} value={form.msp_id}
                onChange={e => setForm(f => ({ ...f, msp_id: e.target.value }))}>
                <option value="">Selecciona un proveedor</option>
                {msps.map(m => <option key={m.msp_id} value={m.msp_id}>{m.nombre}</option>)}
              </select>
            </label>
            <label className="block">ID del administrador AXS
              <input className={field} value={form.owner_user_id} maxLength={100}
                onChange={e => { setForm(f => ({ ...f, owner_user_id: e.target.value })); setOwner(null); }} />
            </label>
            <div className="sm:col-span-2">
              <button type="button" className="min-h-11 rounded border border-gray-600 px-4 py-2" onClick={() => void checkOwner()}>
                Verificar administrador
              </button>
              {owner && <p className="mt-2 text-sm text-gray-200">Usuario verificado: {owner.nombre} · {owner.email}</p>}
            </div>
            <label className="block">Contacto de privacidad
              <input type="email" className={field} value={form.privacy_contact} maxLength={254}
                onChange={e => setForm(f => ({ ...f, privacy_contact: e.target.value }))} />
            </label>
            <label className="block">Versión del aviso de privacidad
              <input className={field} value={form.privacy_notice_version} maxLength={80}
                onChange={e => setForm(f => ({ ...f, privacy_notice_version: e.target.value }))} />
            </label>
            <label className="block sm:col-span-2">URL HTTPS del aviso de privacidad
              <input type="url" className={field} value={form.privacy_notice_url} maxLength={500}
                onChange={e => setForm(f => ({ ...f, privacy_notice_url: e.target.value }))} />
            </label>
            <button className={primary + " sm:col-span-2"} type="button" onClick={prepareCreate}>Revisar alta de empresa</button>
          </fieldset>
          {requestId && <p className="break-all text-xs text-gray-400">Referencia reutilizable del alta: {requestId}</p>}
          <button type="button" className="min-h-11 rounded border border-gray-600 px-4" disabled={busy || !!pending} onClick={resetCompany}>Nueva empresa</button>
        </section>

        <section className="rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-3">
          <h2 className="text-lg font-semibold">Retomar empresa existente</h2>
          <form onSubmit={e => { e.preventDefault(); void loadCompany(); }} className="space-y-2">
            <label className="block">Identificador corporativo
              <input className={field} placeholder="corp_…" value={lookup} disabled={busy || !!pending} maxLength={37}
                onChange={e => setLookup(e.target.value)} />
            </label>
            <button className={primary} disabled={busy || !!pending}>Consultar empresa</button>
          </form>
        </section>

        {company && <section className="rounded-xl border border-blue-800 bg-gray-900 p-4 space-y-4">
          <h2 className="text-lg font-semibold">2. Configuración del directorio</h2>
          <p className="break-all font-medium">{company.nombre} · {company.tenant_id}</p>
          <p className="text-sm text-gray-300">Owner: {company.owner_user_id} · Aviso: {company.privacy_notice_version}</p>
          <p className="text-sm">{company.directorio_habilitado ? "Directorio habilitado" : "Directorio sin habilitar"}</p>
          {!company.directorio_habilitado && <fieldset disabled={locked} className="space-y-3 disabled:opacity-60">
            <label className="block">Máximo de sedes
              <input type="number" min={1} max={1000} className={field} value={limits.max_sedes}
                onChange={e => setLimits(f => ({ ...f, max_sedes: e.target.value }))} />
            </label>
            <label className="block">Máximo de destinos por sede
              <input type="number" min={1} max={2000} className={field} value={limits.max_destinos_por_sede}
                onChange={e => setLimits(f => ({ ...f, max_destinos_por_sede: e.target.value }))} />
            </label>
            <button className={primary} onClick={prepareLimits}>Revisar capacidades</button>
          </fieldset>}
          {!company.directorio_habilitado && <div className="border-t border-gray-700 pt-4 space-y-2">
            <h2 className="font-semibold">3. Habilitación del directorio</h2>
            <p className="text-sm text-gray-300">Requiere cuotas confirmadas, owner y aviso. No habilita el ingreso de visitantes.</p>
            <button className={primary} disabled={locked || !company.capacidades?.max_sedes || !company.capacidades?.max_destinos_por_sede}
              onClick={prepareActivation}>Revisar habilitación</button>
          </div>}
        </section>}

        {pending && <section ref={confirmation} tabIndex={-1} aria-label="Confirmar operación corporativa"
          className="scroll-mt-4 rounded-xl border border-amber-600 p-4 space-y-3 break-words">
          <h2 className="text-lg font-semibold">Confirmar operación</h2>
          <p>{pending.detail}</p>
          <dl className="text-sm">
            {Object.entries(pending.payload).filter(([key]) => key !== "privacy_contact").map(([key, value]) =>
              <div className="my-1" key={key}><dt className="inline text-gray-400">{key}: </dt>
                <dd className="inline break-all">{String(value)}</dd></div>)}
          </dl>
          <div className="flex flex-wrap gap-3">
            <button className={primary} disabled={busy} onClick={() => void execute()}>Confirmar operación</button>
            <button className="min-h-11 rounded border border-gray-600 px-5" disabled={busy} onClick={() => setPending(null)}>Cancelar</button>
          </div>
        </section>}
      </>}
    </div>
  </main>;
}
