'use client';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { api } from '@/lib/api';
import { basePath, blockers, closeOperation, mexicoTime, type Contract, type Inventory, type Operation, type Snapshot } from '@/lib/provider-contracts';

const inputClass = 'block w-full rounded border border-gray-600 bg-gray-900 p-2 mt-1';
const buttonClass = 'rounded bg-blue-600 px-4 py-2 disabled:opacity-40';

export default function ProviderConsole() {
  const { userId } = useAuth();
  return <ContractPanel key={userId ?? "signed-out"} />;
}

function ContractPanel() {
  const { getToken } = useAuth();
  const [tenant, setTenant] = useState('');
  const [selected, setSelected] = useState('');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [pending, setPending] = useState<Operation | null>(null);
  const confirmation = useRef<HTMLElement>(null);
  useEffect(() => {
    if (pending) {
      confirmation.current?.scrollIntoView({ block: 'start', behavior: 'instant' });
      confirmation.current?.focus({ preventScroll: true });
    }
  }, [pending]);
  const [reason, setReason] = useState('');
  const [provider, setProvider] = useState('');
  const [evidence, setEvidence] = useState('');
  const [person, setPerson] = useState('');
  const [scopeId, setScopeId] = useState('');
  const [kind, setKind] = useState('msp');
  const lock = useRef(false);
  // Keep the exact request after a network failure. A retry never creates another UUID.
  const opening = useRef<{ key: string; id: string } | null>(null);
  const current = snapshot?.contracts.find(c => !c.closed_at);
  const unknown = snapshot ? blockers(snapshot) : [];
  async function token() {
    const value = await getToken();
    if (!value) throw new Error('Inicia sesión para continuar');
    return value;
  }
  async function read(id: string, auth: string) {
    const path = basePath(id);
    const [contracts, inventory] = await Promise.all([
      api.get<Contract[]>(`${path}/proveedor/contratos`, auth),
      api.get<Inventory>(`${path}/permisos/procedencia`, auth),
    ]);
    return { contracts, inventory };
  }
  async function load() {
    if (lock.current || !tenant.trim()) return;
    lock.current = true; setBusy(true); setError(''); setSnapshot(null); setPending(null); setReceipt(null);
    const id = tenant.trim(); setScopeId(''); setReason(''); setPerson('');
    try { setSnapshot(await read(id, await token())); setSelected(id); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo consultar'); }
    finally { lock.current = false; setBusy(false); }
  }
  function prepareOpen() {
    if (!provider.trim() || !evidence.trim()) return;
    const key = JSON.stringify([selected, provider.trim(), evidence.trim()]);
    if (opening.current?.key !== key) opening.current = { key, id: crypto.randomUUID() };
    setPending({ method: 'post', path: `${basePath(selected)}/proveedor/contratos`,
      body: { contract_id: opening.current.id, msp_id: provider.trim(), evidence_ref: evidence.trim() },
      label: `Abrir contrato nuevo con ${provider.trim()}`,
      description: 'Se abrirá un contrato independiente. Los permisos revocados de contratos anteriores seguirán revocados; debes otorgar permisos nuevos al personal.' });
  }
  async function execute() {
    if (!pending || lock.current) return;
    const operation = pending;
    lock.current = true; setBusy(true); setError(''); setReceipt(null);
    try {
      const auth = await token();
      const result = await api[operation.method]<Record<string, unknown>>(operation.path, operation.body, auth);
      setReceipt(result); setPending(null);
      if (operation.path.endsWith('/proveedor/contratos')) opening.current = null;
      // A failed refresh must not leave stale mutation controls enabled.
      setSnapshot(null);
      try { setSnapshot(await read(selected, auth)); }
      catch { setError('Operación registrada. No se pudo actualizar la vista; vuelve a consultar el condominio.'); }
    } catch (e) {
      setError(`${e instanceof Error ? e.message : 'No se pudo confirmar el resultado'}. Puedes reintentar la misma solicitud o consultar de nuevo.`);
    } finally { lock.current = false; setBusy(false); }
  }
  return <main className="min-h-screen bg-gray-950 text-white p-5">
    <div className="max-w-4xl mx-auto space-y-6">
      <a href="/dashboard" className="text-blue-300">← Inicio</a>
      <header><h1 className="text-2xl font-bold">Contratos de proveedores</h1>
        <p className="text-gray-300 mt-2">Baja, recontratación e historial por condominio. Exclusivo del operador de plataforma.</p></header>
      <form onSubmit={e => { e.preventDefault(); void load(); }} className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3">
        <label className="flex-1 min-w-0">ID del condominio<input className={inputClass} value={tenant} disabled={busy || !!pending}
          onChange={e => { setTenant(e.target.value); setSnapshot(null); setReceipt(null); }} required /></label>
        <button className={buttonClass} disabled={busy || !!pending}>Consultar</button>
      </form>
      {busy && <p role="status">Procesando…</p>}
      {error && <p role="alert" className="text-amber-300">{error}</p>}
      {receipt && <section role="status" className="border border-green-700 rounded p-4">
        <h2 className="font-bold">Comprobante recibido</h2><pre className="whitespace-pre-wrap break-all text-xs mt-2">{JSON.stringify(receipt, null, 2)}</pre></section>}
      {pending && <section ref={confirmation} tabIndex={-1} aria-label="Confirmar operación" className="border border-amber-500 rounded p-4 space-y-3 break-words scroll-mt-4">
        <h2 className="font-bold">{pending.label}</h2><p>Condominio: {selected}</p>
        <p>{pending.description}</p>
        <details><summary>Datos de la solicitud</summary><pre className="text-xs whitespace-pre-wrap break-all">{JSON.stringify(pending.body, null, 2)}</pre></details>
        <button className={buttonClass} disabled={busy} onClick={() => void execute()}>Confirmar operación</button>{' '}
        <button disabled={busy} onClick={() => setPending(null)}>Cancelar</button>
      </section>}
      {snapshot && <>
        <section className="border border-gray-700 rounded p-4 space-y-2 break-words">
          <h2 className="font-bold">{selected} · {snapshot.inventory.msp_id ? `Proveedor: ${snapshot.inventory.msp_id}` : 'Sin proveedor vigente'}</h2>
          <p>{current ? `Contrato ${current.version} · ${current.contract_id}` : snapshot.inventory.msp_id ? 'Relación anterior sin contrato versionado' : 'Puedes iniciar un contrato nuevo'}</p>
          {unknown.length > 0 && <p className="text-amber-300">Baja bloqueada: revisa procedencia de permisos {unknown.map(s => s.scope_id).join(', ')}.</p>}
        </section>
        <fieldset disabled={busy || !!pending} className="space-y-5 disabled:opacity-60">
          {snapshot.inventory.msp_id ? <form onSubmit={e => { e.preventDefault(); try { setPending(closeOperation(snapshot, reason)); } catch (err) { setError((err as Error).message); } }} className="space-y-3">
            <label>Motivo de baja<textarea className={inputClass} value={reason} onChange={e => setReason(e.target.value)} required maxLength={500} /></label>
            <button className={buttonClass} disabled={unknown.length > 0 || !reason.trim()}>Revisar baja</button>
          </form> : <form onSubmit={e => { e.preventDefault(); prepareOpen(); }} className="space-y-3">
            <h2 className="font-semibold">Nuevo contrato / recontratación</h2>
            <label className="block">ID del proveedor existente<input className={inputClass} value={provider} onChange={e => setProvider(e.target.value)} required maxLength={100} /></label>
            <label className="block">Referencia del contrato o evidencia<input className={inputClass} value={evidence} onChange={e => setEvidence(e.target.value)} required maxLength={500} /></label>
            <button className={buttonClass} disabled={!provider.trim() || !evidence.trim()}>Revisar apertura</button>
          </form>}
          {current && <form className="space-y-3" onSubmit={e => { e.preventDefault(); setPending({ method: 'post',
            path: `${basePath(selected)}/proveedor/contratos/${encodeURIComponent(current.contract_id)}/personal/${encodeURIComponent(person.trim())}`,
            body: { evidence_ref: evidence.trim() }, label: `Otorgar permiso nuevo a ${person.trim()}`,
            description: `Se otorgará un permiso vinculado al contrato ${current.version}. Los permisos revocados de contratos anteriores seguirán revocados.` }); }}>
            <h2 className="font-semibold">Reincorporar personal existente</h2>
            <label className="block">ID del guardia o administrador<input className={inputClass} value={person} onChange={e => setPerson(e.target.value)} required /></label>
            <label className="block">Referencia de autorización<input className={inputClass} value={evidence} onChange={e => setEvidence(e.target.value)} required maxLength={500} /></label>
            <button className={buttonClass} disabled={!person.trim() || !evidence.trim()}>Revisar permiso nuevo</button>
          </form>}
          <details><summary>Registrar procedencia pendiente</summary>
            <p className="text-sm text-gray-300 mt-2">Revisa evidencia antes de atribuir un permiso. Una procedencia registrada no puede cambiarse aquí.</p>
            <form className="space-y-3 mt-3" onSubmit={e => { e.preventDefault(); setPending({method: 'put',
              path: `${basePath(selected)}/permisos/${scopeId}/procedencia`,
              body: { kind, evidence_ref: evidence.trim(), ...(kind === 'msp' ? {msp_id: snapshot.inventory.msp_id} : {}) },
              label: `Registrar permiso ${scopeId} como ${kind === 'msp' ? 'del proveedor' : 'propio del condominio'}`,
              description: 'Se registrará la procedencia del permiso con la evidencia indicada. Una procedencia registrada no puede cambiarse aquí.'}); }}>
              <label className="block">Permiso<select className={inputClass} value={scopeId} onChange={e => setScopeId(e.target.value)} required>
                <option value="">Selecciona</option>{snapshot.inventory.scopes.filter(s => !['msp','condominio'].includes(s.origin.kind ?? '')).map(s => <option key={s.scope_id} value={s.scope_id}>{s.scope_id} · {s.usuario_id}</option>)}
              </select></label>
              <label className="block">Procedencia<select className={inputClass} value={kind} onChange={e => setKind(e.target.value)}><option value="msp">Proveedor vigente</option><option value="condominio">Condominio</option></select></label>
              <label className="block">Referencia de evidencia<input className={inputClass} value={evidence} onChange={e => setEvidence(e.target.value)} required maxLength={500} /></label>
              <button className={buttonClass} disabled={!scopeId || !evidence.trim() || (kind === 'msp' && !snapshot.inventory.msp_id)}>Revisar procedencia</button>
            </form>
          </details>
        </fieldset>
        <section className="space-y-3"><h2 className="text-xl font-semibold">Permisos y procedencia</h2>
          {snapshot.inventory.scopes.map(s => <p key={s.scope_id} className="border-b border-gray-800 pb-2 break-words">#{s.scope_id} · {s.usuario_id} · {s.estado} · {s.origin.kind ?? 'unknown'}{s.origin.contract_id ? ` · ${s.origin.contract_id}` : ''}</p>)}
        </section>
        <section className="space-y-3"><h2 className="text-xl font-semibold">Historial de contratos</h2><p className="text-sm text-gray-400">Horas de Ciudad de México.</p>
          {snapshot.contracts.length === 0 && <p>Sin contratos versionados.</p>}
          {snapshot.contracts.map(c => <article key={c.contract_id} className="border border-gray-700 p-4 rounded space-y-1 break-words">
            <h3 className="font-bold">Contrato {c.version} · {c.msp_id} · {c.closed_at ? 'Cerrado' : 'Vigente'}</h3>
            <p className="text-xs">{c.contract_id}</p><p>Apertura: {mexicoTime(c.opened_at)} · {c.opened_by}</p>
            {c.closed_at && <p>Cierre: {mexicoTime(c.closed_at)}</p>}<p>Referencia: {c.evidence_ref}</p>
            <details><summary>Auditoría</summary><p className="text-xs">Apertura: {c.open_event_uid}<br />Cierre: {c.close_event_uid ?? 'Pendiente'}</p></details>
          </article>)}
        </section>
      </>}
    </div>
  </main>;
}
