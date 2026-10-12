// One-shot Railway/Bun runner. No public endpoint, credentials or tokens in logs.
import { createHmac } from "node:crypto";

const API = "https://axs-development-backend-production.up.railway.app";
const RUN = "AXS RETENTION development 20261012";
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


const SYNTHETIC_JPEG="/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAJYAlgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDCooor6I+aCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAP//Z";
let checks=0;
async function req(actor:string|null,method:string,path:string,expected:number,body?:unknown) {
 const response=await fetch(API+path,{method,redirect:"error",signal:AbortSignal.timeout(90000),
 headers:{...(actor?{Authorization:`Bearer ${token(actor)}`}:{}),...(body?{"Content-Type":"application/json"}:{})},
 ...(body?{body:JSON.stringify(body)}:{})});
 checks++;
 console.log("AXS_RETENTION_CHECK "+JSON.stringify({method,HTTP:response.status,expected,check:checks}));
 check(response.status===expected,`HTTP ${response.status}, expected ${expected}`);
 return response;
}
async function json(actor:string,method:string,path:string,body?:unknown) {return (await req(actor,method,path,200,body)).json();}
async function runRetentionPilot() {
 check(env.APP_ENV==="development"&&env.NEON_DEV_ENDPOINT==="ep-withered-resonance-b59tusv3","Development only");
 const phase=env.AXS_RETENTION_SMOKE_PHASE??"closed", proof:any[]=[];
 for(const side of ["a","b"]) {
  const actor=`axs_demo_admin_${side}`,own=`axs_demo_condo_${side}`,other=`axs_demo_admin_${side==="a"?"b":"a"}`;
  const label=`${RUN} ${side.toUpperCase()}`;
  const visits=await json(actor,"GET",`/visitas/condominio/${own}`);
  const found=visits.filter((v:any)=>v.nombre_visitante===label);
  check(found.length<=1,"Duplicate fixtures");
  let visit=found[0];
  if(phase==="setup"&&!visit) {
   const houses=await json(actor,"GET",`/condominios/${own}/casas`);
   const home=houses.casas.find((h:any)=>h.tipo==="casa")??houses.casas.find((h:any)=>h.tipo==="administracion");
   check(!!home,"Synthetic destination missing");
   visit=await json(actor,"POST",`/visitas/${own}`,{condominio_id:own,nombre_visitante:label,tipo_visita:"eventual",destino_id:home.casa_id,vigencia:new Date(Date.now()+86400000).toISOString()});
  }
  check(!!visit&&visit.condominio_id===own,"Existing fixture required");
  const id=visit.visita_id, query=`?condominio_id=${own}`,path=`/identificaciones/${id}`;
  if(phase==="setup"&&visit.estado==="pendiente")visit=await json(actor,"PATCH",`/visitas/${id}/cancelar${query}`);
  check(visit.estado==="cancelada","Cancelled synthetic visit required");
  let pair=await json(actor,"GET",path+query);
  if(phase==="setup"&&pair.estado==="sin_identificacion") {
   const form=new FormData(),capture=crypto.randomUUID(),bytes=Uint8Array.from(atob(SYNTHETIC_JPEG),c=>c.charCodeAt(0));
   form.append("nombre","AXS documento ficticio - prueba automatica");form.append("captura_id",capture);
   for(const field of ["frente","reverso"])form.append(field,new Blob([bytes],{type:"image/jpeg"}),field+".jpg");
   const response=await fetch(API+path+query,{method:"POST",headers:{Authorization:`Bearer ${token(actor)}`},body:form,signal:AbortSignal.timeout(90000)});
   check(response.status===200,"Synthetic enrollment failed");
   pair=await json(actor,"GET",path+query);
  }
  const holdPath=path+"/conservacion/excepcion"+query, cyclePath=path+"/conservacion/ciclo-prueba"+query;
  const body={hasta:new Date(Date.now()+86400000).toISOString(),responsable:"Operador ficticio",incidencia:"AXS-RETENTION-TEST-20261012",motivo:"Validación ficticia de caducidad y excepción"};
  if(phase==="setup") {
   check(pair.evidencias.length===2&&["vigente","excepcion"].includes(pair.conservacion?.estado),"Pair not enrolled");
   await req(other,"PUT",holdPath,403,body);await req(null,"PUT",holdPath,401,body);
   await json(actor,"PUT",holdPath,body);
   for(const e of pair.evidencias)await req(actor,"GET",path+"/"+e.evidencia_id+query,200);
   await json(actor,"DELETE",holdPath);
   if(side==="a")await json(actor,"PUT",holdPath,body);
   proof.push({tenant:own,visit:id,eids:pair.evidencias.map((e:any)=>e.evidencia_id),capture:pair.evidencias[0].captura_id});
   continue;
  }
  const configured=JSON.parse(env.AXS_RETENTION_SMOKE_PROOF??"[]").find((p:any)=>p.visit===id);
  check(!!configured,"Fixture proof required");
  if(phase==="verify"&&pair.estado!=="eliminada") {
   if(side==="a") {
    check(pair.conservacion?.estado==="excepcion"&&pair.evidencias.length===2,"Hold did not preserve access");
    for(const eid of configured.eids)await req(actor,"GET",path+"/"+eid+query,200);
    const skipped=await json(actor,"POST",cyclePath);
    check(skipped.reclamados===0&&skipped.completados===0,"Held pair claimed");
    await json(actor,"DELETE",holdPath);
    pair=await json(actor,"GET",path+query);
   }
   check(pair.estado==="vencida"&&pair.evidencias.length===0,"Expired pair disclosed metadata");
   for(const eid of configured.eids)await req(actor,"GET",path+"/"+eid+query,410);
   const concurrent=await Promise.all([json(actor,"POST",cyclePath),json(actor,"POST",cyclePath)]);
   check(concurrent.reduce((n:number,r:any)=>n+r.reclamados,0)===1&&concurrent.reduce((n:number,r:any)=>n+r.completados,0)===1,"Workers duplicated or failed deletion");
   const repeated=await json(actor,"POST",cyclePath);
   check(repeated.reclamados===0&&repeated.completados===0,"Completed pair reclaimed");
  }
  pair=await json(actor,"GET",path+query);
  check(pair.estado==="eliminada"&&pair.evidencias.length===0,"Elimination not finalized");
  for(const eid of configured.eids)await req(actor,"GET",path+"/"+eid+query,410);
  if(phase==="closed") {
   await req(actor,"POST",cyclePath,404);
   await req(actor,"PUT",holdPath,404,body);
   check(pair.puede_gestionar_conservacion===false,"Disabled pilot still offers controls");
  }
  let audit:any;
  for(let attempt=0;attempt<8;attempt++){
   const history=await json(actor,"GET",`/bitacora/${own}?visita_id=${id}&limite=100`);
   const completions=history.items.filter((e:any)=>e.accion==="eliminar_identificacion");
   if(completions.length){check(completions.length===1&&completions[0].resultado==="exito","Audit duplicated or failed");audit=completions[0];break;}
   await Bun.sleep(6000);
  }
  check(!!audit,"Audit not delivered");
  const after=await json(actor,"GET",`/visitas/${id}${query}`);
  check(after.estado==="cancelada"&&!after.salida_registrada_en,"Visit state changed");
  const cutoff=new Date().toLocaleDateString("en-CA",{timeZone:"America/Mexico_City"});
  const report=await json(actor,"GET",`/reportes/${own}/identificaciones-vencimiento?fecha_corte=${cutoff}`);
  check(!report.items.some((item:any)=>item.visita_id===id),"Purged photos still counted");
  proof.push({...configured,event_uid:audit.event_uid,delivery:410,audit_delivered:true,idempotent:true});
 }
 console.log("AXS_RETENTION_LIVE_RESULT "+JSON.stringify({status:"PASS",phase,checks,synthetic_only:true,proof}));
}
try { await runRetentionPilot(); } catch(e) {console.error("AXS_RETENTION_LIVE_RESULT "+JSON.stringify({status:"FAIL",phase:env.AXS_RETENTION_SMOKE_PHASE,checks,error:e instanceof Error?e.message:"unknown"}));}
