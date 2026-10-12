// One-shot Railway/Bun runner. No public endpoint, credentials or tokens in logs.
import { createHmac } from "node:crypto";

const API = "https://axs-development-backend-production.up.railway.app";
const RUN = "AXS AUTO development 20261003-visit-v1";
const env = process.env;
const results: object[] = [];
const created: { tenant: string; visit: string; actor: string }[] = [];

function check(ok: boolean, message: string) {
  if (!ok) throw new Error(message);
}

function token(actor: string) {
  const encode = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const now = Math.floor(Date.now() / 1000);
  const body = encode({ alg: "HS256", typ: "JWT" }) + "." +
    encode({ sub: actor, role: "MSP_ADMIN", method: "local", iat: now, exp: now + 300 });
  return body + "." + createHmac("sha256", env.AXS_TEST_SECRET!).update(body).digest("base64url");
}

async function request(actor: string, method: string, path: string, expected: number, body?: object) {
  const response = await fetch(API + path, {
    method, redirect: "error", signal: AbortSignal.timeout(30000),
    headers: { Authorization: `Bearer ${token(actor)}`, "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  results.push({ actor, method, path, HTTP: response.status, expected });
  console.log("AXS_SMOKE_CHECK " + JSON.stringify(results.at(-1)));
  check(response.status === expected, `Unexpected HTTP ${response.status}: ${method} ${path}`);
  return response.json();
}

async function run() {
  check(env.APP_ENV === "development", "Development environment required");
  check(env.NEON_DEV_ENDPOINT === "ep-withered-resonance-b59tusv3", "Development endpoint required");
  check(!!env.AXS_TEST_SECRET && !env.AXS_TEST_SECRET.includes("${{"), "Runtime secret reference required");
  for (const side of ["a", "b"]) {
    const actor = `axs_demo_admin_${side}`;
    const otherActor = `axs_demo_admin_${side === "a" ? "b" : "a"}`;
    const own = `axs_demo_condo_${side}`;
    const other = `axs_demo_condo_${side === "a" ? "b" : "a"}`;
    const me = await request(actor, "GET", "/auth/me", 200);
    check(me.usuario_id === actor && me.rol === "MSP_ADMIN", "Identity mismatch");
    const houseResponse = await request(actor, "GET", `/condominios/${own}/casas`, 200);
    const home = houseResponse.casas.find((h: any) => h.tipo === "casa") ??
      houseResponse.casas.find((h: any) => h.tipo === "administracion");
    check(!!home?.casa_id, "Own catalog destination required");
    const label = `${RUN} ${side.toUpperCase()}`;
    const body = { condominio_id: own, nombre_visitante: label, tipo_visita: "eventual",
      destino_id: home.casa_id, vigencia: new Date(Date.now() + 86400000).toISOString() };
    const visits = await request(actor, "GET", `/visitas/condominio/${own}`, 200);
    const existing = visits.filter((v: any) => v.nombre_visitante === label);
    check(existing.length <= 1, "Duplicate smoke visits; review required");
    const visit = existing[0] ?? await request(actor, "POST", `/visitas/${own}`, 200, body);
    check(visit.condominio_id === own, "Created visit tenant mismatch");
    check(["pendiente", "cancelada"].includes(visit.estado), "Unexpected smoke visit state");
    created.push({ tenant: own, visit: visit.visita_id, actor });
    console.log("AXS_SMOKE_VISIT " + JSON.stringify(created.at(-1)));
    await request(actor, "POST", `/visitas/${other}`, 403, { ...body, condominio_id: other });
    await request(actor, "POST", `/visitas/${own}`, 400, { ...body, condominio_id: other });
    await request(otherActor, "PATCH", `/visitas/${visit.visita_id}/cancelar?condominio_id=${own}`, 403);
    const unchanged = await request(actor, "GET", `/visitas/${visit.visita_id}?condominio_id=${own}`, 200);
    check(unchanged.estado === visit.estado, "Cross cancellation changed visit");
    if (unchanged.estado === "pendiente") {
      await request(actor, "PATCH", `/visitas/${visit.visita_id}/cancelar?condominio_id=${own}`, 200);
    }
    const final = await request(actor, "GET", `/visitas/${visit.visita_id}?condominio_id=${own}`, 200);
    check(final.estado === "cancelada", "Own cancellation did not persist");
    const after = await request(actor, "GET", `/visitas/condominio/${own}`, 200);
    check(after.filter((v: any) => v.nombre_visitante === label).length === 1, "Unexpected created visit count");
  }
  console.log("AXS_SMOKE_RESULT " + JSON.stringify({ status: "PASS", run: RUN, checks: results.length, created }));
}

// Synthetic-only live checks: existing isolated accounts and disposable smoke visits.
const SYNTHETIC_JPEG = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAJYAlgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDCooor6I+aCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAP//Z";
type IdentityRow = { evidencia_id: string; lado: string; nombre: string };
let identityChecks = 0;
async function identityRequest(actor: string | null, path: string, expected: number[], form?: FormData) {
  const response = await fetch(API + path, {
    method: form ? "POST" : "GET", redirect: "error", signal: AbortSignal.timeout(30000),
    headers: actor ? { Authorization: `Bearer ${token(actor)}` } : {},
    ...(form ? { body: form } : {}),
  });
  identityChecks++;
  console.log("AXS_ID_CHECK " + JSON.stringify({ actor: actor ?? "anonymous", HTTP: response.status, expected, check: identityChecks }));
  check(expected.includes(response.status), `Identity check ${identityChecks}: unexpected HTTP ${response.status}`);
  return response;
}

async function runIdentity() {
  check(env.APP_ENV === "development", "Development only");
  check(env.NEON_DEV_ENDPOINT === "ep-withered-resonance-b59tusv3", "Development endpoint required");
  check(!!env.AXS_TEST_SECRET && !env.AXS_TEST_SECRET.includes("${{"), "Runtime secret required");
  for (const side of ["a", "b"]) {
    const actor = `axs_demo_admin_${side}`;
    const otherActor = `axs_demo_admin_${side === "a" ? "b" : "a"}`;
    const own = `axs_demo_condo_${side}`;
    const other = `axs_demo_condo_${side === "a" ? "b" : "a"}`;
    const me = await request(actor, "GET", "/auth/me", 200);
    check(me.usuario_id === actor && me.rol === "MSP_ADMIN", "Wrong test account");
    const visits = await request(actor, "GET", `/visitas/condominio/${own}`, 200);
    const matches = visits.filter((v: {nombre_visitante: string}) => v.nombre_visitante === `${RUN} ${side.toUpperCase()}`);
    check(matches.length === 1, "Exactly one existing synthetic visit required");
    const visit = matches[0];
    const path = `/identificaciones/${encodeURIComponent(visit.visita_id)}`;
    const ownQuery = `?condominio_id=${own}`;
    const otherQuery = `?condominio_id=${other}`;
    const list = await identityRequest(actor, path + ownQuery, [200]);
    check(list.headers.get("cache-control")?.includes("no-store"), "Metadata caching prohibited");
    let rows: IdentityRow[] = (await list.json()).evidencias;
    if (!rows.length) {
      const form = new FormData();
      form.append("nombre", "AXS documento ficticio - prueba automatica");
      form.append("captura_id", side === "a" ? "ec042124-9fbf-4b1a-b5fd-792b26dde121" : "c51320c8-78c0-42a1-9d1f-26a29940222c");
      const bytes = Buffer.from(SYNTHETIC_JPEG, "base64");
      form.append("frente", new Blob([bytes], { type: "image/jpeg" }), "synthetic-front.jpg");
      form.append("reverso", new Blob([bytes], { type: "image/jpeg" }), "synthetic-back.jpg");
      rows = (await (await identityRequest(actor, path + ownQuery, [200], form)).json()).evidencias;
    }
    check(rows.length === 2 && new Set(rows.map(row => row.lado)).size === 2, "Distinct front and back required");
    check(rows.every(row => row.nombre === "AXS documento ficticio - prueba automatica"), "Refuse to read non-synthetic identification");
    await identityRequest(otherActor, path + ownQuery, [403]);
    await identityRequest(otherActor, path + otherQuery, [404]);
    await identityRequest(null, path + ownQuery, [401]);
    for (const row of rows) {
      const photoPath = `${path}/${encodeURIComponent(row.evidencia_id)}`;
      const photo = await identityRequest(actor, photoPath + ownQuery, [200]);
      check(photo.headers.get("content-type")?.startsWith("image/jpeg"), "Photo type mismatch");
      check(photo.headers.get("cache-control")?.includes("private") && photo.headers.get("cache-control")?.includes("no-store"), "Photo caching prohibited");
      check((await photo.arrayBuffer()).byteLength > 0, "Empty photo");
      await identityRequest(otherActor, photoPath + ownQuery, [403]);
      await identityRequest(otherActor, photoPath + otherQuery, [404]);
      await identityRequest(null, photoPath + ownQuery, [401]);
    }
    const after = await request(actor, "GET", `/visitas/${visit.visita_id}?condominio_id=${own}`, 200);
    check(after.estado === visit.estado, "Identity changed visit state");
  }
  console.log("AXS_ID_RESULT " + JSON.stringify({ status: "PASS", checks: identityChecks, tenants: 2, synthetic: true, auth: "existing-local-test-accounts" }));
}


async function runRetention() {
  let checks = 0;
  for (const side of ["a", "b"]) {
    const actor = `axs_demo_admin_${side}`;
    const otherActor = `axs_demo_admin_${side === "a" ? "b" : "a"}`;
    const own = `axs_demo_condo_${side}`;
    const visits = await request(actor, "GET", `/visitas/condominio/${own}`, 200);
    const visit = visits.find((v: {nombre_visitante: string}) => v.nombre_visitante === `${RUN} ${side.toUpperCase()}`);
    check(!!visit, "Existing synthetic visit required");
    const pairPath = `/identificaciones/${encodeURIComponent(visit.visita_id)}?condominio_id=${own}`;
    const before = await request(actor, "GET", pairPath, 200);
    const route = `/reportes/${own}/identificaciones-vencimiento?fecha_corte=2026-12-01`;
    const response = await identityRequest(actor, route, [200]);
    checks++;
    const report = await response.json();
    check(report.modo === "simulacion" && report.borrado_activado === false, "Read-only simulation required");
    check(response.headers.get("cache-control")?.includes("no-store"), "Private report caching prohibited");
    const item = report.items.find((i: {visita_id: string}) => i.visita_id === visit.visita_id);
    check(item?.clasificacion === "venceria" && item.fotos === 2, "Known synthetic pair should reach proposed deadline");
    const json = JSON.stringify(report);
    check(!json.includes("archivo_url") && !json.includes("captura_id") && !json.includes("nombre") && !json.includes("axs-identificaciones/"), "Report exposes identity details");
    await identityRequest(otherActor, route, [403]); checks++;
    await identityRequest(null, route, [401]); checks++;
    const after = await request(actor, "GET", pairPath, 200);
    check(JSON.stringify(before) === JSON.stringify(after), "Simulation altered evidence metadata");
  }
  console.log("AXS_RETENTION_RESULT " + JSON.stringify({status:"PASS",checks,tenants:2,simulation:true,deletion:false}));
}

try {
  if (!env.AXS_TEST_SECRET) console.log("AXS_SMOKE_WAITING runtime variables required");
  else { await runIdentity(); await runRetention(); }
} catch (error) {
  // Exit successfully so Railway does not retry writes automatically. FAIL is explicit.
  console.error("AXS_ID_RESULT " + JSON.stringify({ status: "FAIL", run: RUN,
    error: error instanceof Error ? error.message : "Runner failed", checks: results.length, created }));
}
