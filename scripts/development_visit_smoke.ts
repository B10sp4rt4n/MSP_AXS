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
    const home = houseResponse.casas.find((h: any) => h.tipo === "casa");
    check(!!home?.casa_id, "Own residential destination required");
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

try {
  if (!env.AXS_TEST_SECRET) console.log("AXS_SMOKE_WAITING runtime variables required");
  else await run();
} catch (error) {
  // Exit successfully so Railway does not retry writes automatically. FAIL is explicit.
  console.error("AXS_SMOKE_RESULT " + JSON.stringify({ status: "FAIL", run: RUN,
    error: error instanceof Error ? error.message : "Runner failed", checks: results.length, created }));
}
