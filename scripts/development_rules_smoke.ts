// One-shot development fixture runner; local JWT, no tokens/secrets in logs.
import { createHmac } from "node:crypto";
const API = "https://axs-development-backend-production.up.railway.app";
const RUN = "axs-rules-20261003";
const A = "axs_demo_admin_a", B = "axs_demo_admin_b";
const G = "axs_rules_guard_20261003", V = "axs_rules_visit_20261003";
const T = "axs_demo_condo_a", OTHER = "axs_demo_condo_b";
const env = process.env;
const checks: object[] = [];
function assert(ok: boolean, message: string) { if (!ok) throw new Error(message); }
function token(actor: string) {
  assert([A, B, G].includes(actor), "Unsupported fixture identity");
  const encode = (v: object) => Buffer.from(JSON.stringify(v)).toString("base64url");
  const now = Math.floor(Date.now()/1000);
  const body = encode({alg:"HS256",typ:"JWT"})+"."+encode({sub:actor,
    role:actor===G?"GUARDIA":"MSP_ADMIN",method:"local",iat:now,exp:now+300});
  return body+"."+createHmac("sha256",env.AXS_TEST_SECRET!).update(body).digest("base64url");
}
async function request(actor: string, method: string, path: string, expected: number, body?: object) {
  const response = await fetch(API+path,{method,redirect:"error",signal:AbortSignal.timeout(30000),
    headers:{Authorization:`Bearer ${token(actor)}`,"Content-Type":"application/json"},
    ...(body?{body:JSON.stringify(body)}:{})});
  checks.push({actor,method,path,HTTP:response.status,expected});
  console.log("AXS_RULES_CHECK "+JSON.stringify(checks.at(-1)));
  assert(response.status===expected,`Unexpected HTTP ${response.status}: ${method} ${path}`);
  return response.json();
}
function same(a: any,b: any) {
  return a.exigir_proposito===b.exigir_proposito && a.exigir_autorizacion===b.exigir_autorizacion &&
    JSON.stringify(a.tipos_visita)===JSON.stringify(b.tipos_visita);
}
async function run() {
  assert(env.APP_ENV==="development" && env.NEON_DEV_ENDPOINT==="ep-withered-resonance-b59tusv3",
    "Development environment required");
  assert(!!env.AXS_TEST_SECRET&&!env.AXS_TEST_SECRET.includes("${{"),"Runtime secret reference required");
  for (const actor of [A,B,G]) {
    const me = await request(actor,"GET","/auth/me",200);
    assert(me.usuario_id===actor && me.rol===(actor===G?"GUARDIA":"MSP_ADMIN"),"Identity mismatch");
  }
  const route=`/condominios/${T}/reglas-acceso`;
  const initial=await request(A,"GET",route,200);
  const other=await request(B,"GET",`/condominios/${OTHER}/reglas-acceso`,200);
  assert(!initial.exigir_proposito&&!initial.exigir_autorizacion,"Fixture tenant rules must start disabled");
  const visitPath=`/visitas/${V}?condominio_id=${T}`;
  const initialVisit=await request(A,"GET",visitPath,200);
  assert(initialVisit.estado==="pendiente"&&!initialVisit.autorizada_por&&!initialVisit.entrada_registrada_en,
    "Fresh pending unauthorized fixture required; never replay a completed run");
  const fixtureTime=Date.parse(initialVisit.vigencia+(/Z$|[+-]\d\d:\d\d$/.test(initialVisit.vigencia)?"":"Z"));
  assert(Number.isFinite(fixtureTime)&&Math.abs(Date.now()-fixtureTime)<15*60000,
    "Prepare fixture vigencia within 15 minutes before running");
  const active={...initial,exigir_proposito:true,exigir_autorizacion:true};
  let rulesMayHaveChanged=false;
  try {
    rulesMayHaveChanged=true;
    await request(A,"PUT",route,200,active);
    await request(G,"PUT",route,403,initial);
    await request(B,"GET",route,403);
    await request(G,"PATCH",`/visitas/${V}/autorizar?condominio_id=${T}`,403,{proposito:"Override"});
    await request(G,"POST",`/visitas/entrada/${T}`,403,{condominio_id:T,nombre_visitante:RUN,
      tipo_visita:"proveedor",destino_id:"axs_demo_casa_a_101",vigencia:new Date().toISOString()});
    await request(G,"PATCH",`/visitas/${V}/entrada?condominio_id=${T}`,403);
    const untouched=await request(A,"GET",visitPath,200);
    assert(untouched.estado==="pendiente"&&!untouched.autorizada_por&&!untouched.entrada_registrada_en,
      "Rejected entry changed fixture");
    const approval=await request(A,"PATCH",`/visitas/${V}/autorizar?condominio_id=${T}`,200,
      {proposito:"Validación de mantenimiento"});
    assert(approval.autorizada_por===A&&!!approval.autorizada_en,"Approval lacks server identity/time");
    const entered=await request(G,"PATCH",`/visitas/${V}/entrada?condominio_id=${T}`,200);
    assert(entered.estado==="entrada_registrada"&&!!entered.entrada_registrada_en,"Entry not persisted");
    await request(G,"PATCH",`/visitas/${V}/entrada?condominio_id=${T}`,400);
    await request(G,"PATCH",`/visitas/${V}/salida?condominio_id=${T}`,200);
    const final=await request(A,"GET",visitPath,200);
    assert(final.estado==="salida_registrada"&&!!final.salida_registrada_en&&final.autorizada_por===A,
      "Final fixture state incorrect");
  } finally {
    if (rulesMayHaveChanged) {
      await request(A,"PUT",route,200,initial);
      assert(same(await request(A,"GET",route,200),initial),"Rules restoration failed");
    }
  }
  assert(same(await request(B,"GET",`/condominios/${OTHER}/reglas-acceso`,200),other),
    "Other tenant configuration changed");
  console.log("AXS_RULES_RESULT "+JSON.stringify({status:"PASS",run:RUN,checks:checks.length,
    visit:V,rulesRestored:true,authentication:"local-jwt"}));
}
try {
  if (!env.AXS_TEST_SECRET) console.log("AXS_RULES_WAITING runtime variables required");
  else await run();
} catch(error) {
  console.error("AXS_RULES_RESULT "+JSON.stringify({status:"FAIL",run:RUN,checks:checks.length,
    error:error instanceof Error?error.message:"Runner failed"}));
  // Never use the exit code as the verdict: no automatic retry of mutations.
}
