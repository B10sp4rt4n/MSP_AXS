// One-shot Bun runner for AXS Development ONLY. No listener, cron or token logging.
import { createHmac } from "node:crypto";

const API = "https://axs-development-backend-production.up.railway.app";
const PREFIX = "lab261009_cycles_v1";
const TENANT = `${PREFIX}_condo`;
const MSP = `${PREFIX}_msp`;
const CONTROL = `${PREFIX}_control`;
const CONTRACTS = ["f8e30960-7c68-42ae-a87c-d7c328da8601", "f8e30960-7c68-42ae-a87c-d7c328da8602"];
const roles = { operator: "MSP_ADMIN", guard: "GUARDIA", stale: "GUARDIA", local: "ADMIN_CONDOMINIO" };
type Actor = keyof typeof roles;
const env = process.env;
const results: object[] = [];
const tokens = new Map<Actor, string>();
let deadline: AbortSignal;

function check(ok: unknown, message: string): asserts ok {
  if (!ok) throw new Error(message);
}

function issueTokens() {
  const encode = (v: object) => Buffer.from(JSON.stringify(v)).toString("base64url");
  const now = Math.floor(Date.now() / 1000);
  for (const actor of Object.keys(roles) as Actor[]) {
    const body = encode({ alg: "HS256", typ: "JWT" }) + "." + encode({
      sub: `${PREFIX}_${actor}`, role: roles[actor], method: "local", iat: now, exp: now + 300,
    });
    tokens.set(actor, body + "." + createHmac("sha256", env.AXS_TEST_SECRET!).update(body).digest("base64url"));
  }
}

async function request(actor: Actor, method: string, path: string, expected: number, body?: object) {
  check(path.startsWith(`/condominios/${TENANT}/`) || path === `/condominios/${CONTROL}/casas`, "Synthetic path required");
  const response = await fetch(API + path, {
    method, redirect: "error", signal: AbortSignal.any([deadline, AbortSignal.timeout(30000)]),
    headers: { Authorization: `Bearer ${tokens.get(actor)}`, "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const result = { actor, method, path, actual: response.status, expected };
  results.push(result);
  console.log("AXS_CYCLES_CHECK " + JSON.stringify(result));
  check(response.status === expected, `Unexpected HTTP ${response.status}: ${method} ${path}`);
  return response.json();
}

const base = `/condominios/${TENANT}`;
const history = () => request("operator", "GET", `${base}/proveedor/contratos`, 200);
const inventory = () => request("operator", "GET", `${base}/permisos/procedencia`, 200);
const access = (actor: Actor, expected: number) => request(actor, "GET", `${base}/casas`, expected);
const open = (cid: string, expected = 200) => request("operator", "POST", `${base}/proveedor/contratos`, expected,
  { contract_id: cid, msp_id: MSP, evidence_ref: `${PREFIX}/${cid}` });
const close = (cid: string) => request("operator", "POST", `${base}/proveedor/baja`, 200,
  { contract_id: cid, msp_id: MSP, reason: `${PREFIX}: synthetic offboarding` });
const grant = (cid: string, actor: "guard" | "stale", expected = 200) => request("operator", "POST",
  `${base}/proveedor/contratos/${cid}/personal/${PREFIX}_${actor}`, expected,
  { evidence_ref: `${PREFIX}/assignment/${cid}/${actor}` });

async function run() {
  check(env.APP_ENV === "development", "Development environment required");
  check(env.NEON_DEV_ENDPOINT === "ep-withered-resonance-b59tusv3", "Development endpoint required");
  check(!!env.AXS_TEST_SECRET && !env.AXS_TEST_SECRET.includes("${{"), "Runtime secret reference required");
  deadline = AbortSignal.timeout(240000);
  issueTokens(); // Exactly ONE token per identity, reused for the entire run.
  check((await history()).length === 0, "Fresh fixture required; never rerun completed or partial fixtures");
  const before = await inventory();
  check(before.msp_id === null && before.scopes.length === 1, "Detached condo with one local scope required");
  const local = before.scopes[0];
  check(local.usuario_id === `${PREFIX}_local` && local.estado === "activo" && local.origin.kind === "condominio", "Local fixture mismatch");
  await request("local", "GET", `${base}/proveedor/contratos`, 403);
  await access("guard", 403);
  await access("stale", 403);
  await access("local", 200);
  await request("guard", "GET", `/condominios/${CONTROL}/casas`, 200);

  const first = await open(CONTRACTS[0]);
  check(first.version === 1 && !first.unchanged, "First contract missing");
  check((await open(CONTRACTS[0])).open_event_uid === first.open_event_uid, "Open retry duplicated event");
  await open(CONTRACTS[1], 409);
  await access("guard", 403);
  const old = await grant(CONTRACTS[0], "guard");
  const stale = await grant(CONTRACTS[0], "stale");
  check((await grant(CONTRACTS[0], "guard")).scope_id === old.scope_id, "Grant retry duplicated scope");
  await access("guard", 200);
  await access("stale", 200);
  await request("operator", "POST", `${base}/proveedor/baja`, 409, { msp_id: MSP, reason: "Missing contract must fail" });
  const receipt1 = await close(CONTRACTS[0]);
  check(receipt1.revoked_scope_ids.length === 2 && receipt1.revoked_scope_ids.includes(old.scope_id) && receipt1.revoked_scope_ids.includes(stale.scope_id), "First revocation mismatch");
  check(receipt1.preserved_scope_ids.includes(local.scope_id), "Local permission not preserved");
  await access("guard", 403);
  await access("stale", 403);
  await access("local", 200);

  const second = await open(CONTRACTS[1]);
  check(second.version === 2 && second.contract_id !== first.contract_id, "Independent second contract missing");
  const retry1 = await close(CONTRACTS[0]);
  check(retry1.unchanged && retry1.event_uid === receipt1.event_uid, "Stale close did not return original receipt");
  check((await history()).find((r: any) => r.contract_id === CONTRACTS[1])?.closed_at === null, "Stale close affected second contract");
  await access("guard", 403);
  await access("stale", 403);
  await grant(CONTRACTS[0], "guard", 409);
  const fresh = await grant(CONTRACTS[1], "guard");
  check(fresh.scope_id !== old.scope_id && fresh.scope_id !== stale.scope_id, "Old grant reused");
  await access("guard", 200);
  await access("stale", 403);
  await access("local", 200);
  const receipt2 = await close(CONTRACTS[1]);
  check(receipt2.event_uid !== receipt1.event_uid && receipt2.revoked_scope_ids.length === 1 && receipt2.revoked_scope_ids[0] === fresh.scope_id, "Second revocation mismatch");
  check(receipt2.preserved_scope_ids.includes(local.scope_id), "Second close lost local permission");
  const retry2 = await close(CONTRACTS[1]);
  check(retry2.unchanged && retry2.event_uid === receipt2.event_uid, "Second close retry duplicated event");
  check((await open(CONTRACTS[0])).closed_at !== null, "Closed contract reopened");
  await access("guard", 403);
  await access("stale", 403);
  await access("local", 200);
  await request("guard", "GET", `/condominios/${CONTROL}/casas`, 200);
  const rows = await history();
  check(rows.length === 2 && rows.every((r: any, i: number) => r.contract_id === CONTRACTS[i] && r.version === i + 1 && r.closed_at && r.open_event_uid && r.close_event_uid), "History mismatch");
  const final = await inventory();
  check(final.msp_id === null && final.scopes.length === 4, "Final inventory mismatch");
  check(JSON.stringify(final.scopes.find((s: any) => s.scope_id === local.scope_id)) === JSON.stringify(local), "Local scope changed");
  for (const [id, cid] of [[old.scope_id, CONTRACTS[0]], [stale.scope_id, CONTRACTS[0]], [fresh.scope_id, CONTRACTS[1]]]) {
    const scope = final.scopes.find((s: any) => s.scope_id === id);
    check(scope?.estado === "revocado" && scope.origin.contract_id === cid, "Revoked grant or provenance changed");
  }
  console.log("AXS_CYCLES_RESULT " + JSON.stringify({ status: "PASS", run: PREFIX, checks: results.length,
    contracts: CONTRACTS, scopes: [old.scope_id, stale.scope_id, fresh.scope_id],
    events: [first.open_event_uid, old.event_uid, stale.event_uid, receipt1.event_uid, second.open_event_uid, fresh.event_uid, receipt2.event_uid],
    reusedTokens: true, clerkTested: false }));
}

try {
  if (!env.AXS_TEST_SECRET) console.log("AXS_CYCLES_WAITING runtime variables required");
  else await run();
} catch (error) {
  // Exit zero to prevent infrastructure retries. PASS requires the explicit result, not service status.
  console.error("AXS_CYCLES_RESULT " + JSON.stringify({ status: "FAIL", run: PREFIX,
    error: error instanceof Error ? error.message : "Runner failed", checks: results.length }));
} finally {
  tokens.clear();
}
