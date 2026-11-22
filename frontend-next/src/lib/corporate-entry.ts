import { api } from "@/lib/api";

export type CorporateWorkspace = { tenant: string; site?: string };
const tenantPattern = /^corp_[A-Za-z0-9_-]{1,100}$/;
const sitePattern = /^site_[A-Za-z0-9_-]{1,50}$/;
const key = (userId: string) => `axs:corporate-workspace:v1:${userId}`;

function valid(value: unknown): value is CorporateWorkspace {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return typeof row.tenant === "string" && tenantPattern.test(row.tenant)
    && (row.site === undefined || (typeof row.site === "string" && sitePattern.test(row.site)));
}

// This is a navigation preference, never an authorization record. No tokens,
// names, roles or responses are persisted, and each Clerk identity has its own key.
export function readCorporateWorkspace(userId: string): CorporateWorkspace | null {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(key(userId)) ?? "null");
    return valid(value) ? { tenant: value.tenant, ...(value.site ? { site: value.site } : {}) } : null;
  } catch { return null; }
}

export function rememberCorporateWorkspace(userId: string, value: CorporateWorkspace) {
  if (!valid(value)) return;
  try {
    window.localStorage.setItem(key(userId), JSON.stringify({ tenant: value.tenant, ...(value.site ? { site: value.site } : {}) }));
  } catch { /* Storage is optional. */ }
}

export function forgetCorporateWorkspace(userId: string) {
  try { window.localStorage.removeItem(key(userId)); } catch { /* Storage is optional. */ }
}

export async function verifiedCorporateEntry(value: CorporateWorkspace, token: string, signal: AbortSignal) {
  if (!valid(value)) throw Error("Contexto corporativo inválido");
  const directory = `/dashboard/corporativo?empresa=${encodeURIComponent(value.tenant)}`;
  if (!value.site) {
    // Existing endpoint checks membership before returning the scoped directory.
    await api.get(`/corporativo/${encodeURIComponent(value.tenant)}/sedes`, token, signal);
    return directory;
  }
  const caps = await api.get<{ role: string }>(
    `/corporativo/${encodeURIComponent(value.tenant)}/sedes/${encodeURIComponent(value.site)}/visitas/capacidades`, token, signal);
  if (["owner", "admin"].includes(caps.role)) return directory;
  if (["host", "reception"].includes(caps.role)) {
    return `/dashboard/corporativo/visitas?empresa=${encodeURIComponent(value.tenant)}&sede=${encodeURIComponent(value.site)}`;
  }
  throw Error("Función corporativa no disponible");
}
