export type Contract = {
  contract_id: string; condominio_id: string; msp_id: string; version: number;
  evidence_ref: string; opened_by: string; opened_at: string;
  closed_at: string | null; open_event_uid: string; close_event_uid: string | null;
};
export type Origin = { kind?: string; msp_id?: string; contract_id?: string };
export type Scope = { scope_id: number; usuario_id: string; estado: string; origin: Origin };
export type Inventory = { condominio_id: string; msp_id: string | null; scopes: Scope[] };
export type Snapshot = { contracts: Contract[]; inventory: Inventory };
export type Operation = { path: string; body: Record<string, unknown>; method: 'post' | 'put'; label: string; description: string };
export function basePath(tenant: string) { return `/condominios/${encodeURIComponent(tenant)}`; }
export function blockers(snapshot: Snapshot) {
  const current = snapshot.contracts.find(c => !c.closed_at);
  return snapshot.inventory.scopes.filter(s => s.estado !== 'revocado' && s.origin.kind !== 'condominio' &&
    !(snapshot.inventory.msp_id && s.origin.kind === 'msp' && s.origin.msp_id === snapshot.inventory.msp_id &&
      (s.origin.contract_id ?? null) === (current?.contract_id ?? null)));
}
export function closeOperation(snapshot: Snapshot, reason: string): Operation {
  const { inventory, contracts } = snapshot;
  if (!inventory.msp_id || !reason.trim()) throw new Error('Proveedor vigente y motivo requeridos');
  if (blockers(snapshot).length) throw new Error('Resuelve la procedencia de los permisos antes de la baja');
  const current = contracts.find(c => !c.closed_at);
  return { method: 'post', path: `${basePath(inventory.condominio_id)}/proveedor/baja`,
    body: { msp_id: inventory.msp_id, reason: reason.trim(), ...(current ? { contract_id: current.contract_id } : {}) },
    label: `Dar de baja a ${inventory.msp_id}${current ? ` · contrato ${current.version}` : ' · relación anterior'}`,
    description: 'La baja revoca los permisos del proveedor y conserva los propios del condominio. El historial se conserva.' };
}
export function mexicoTime(value: string) {
  // The backend serializes naive UTC datetimes; never interpret them as browser local time.
  const utc = /(?:Z|[+-]\d\d:\d\d)$/i.test(value) ? value : `${value}Z`;
  return new Date(utc).toLocaleString('es-MX', { timeZone: 'America/Mexico_City' });
}
