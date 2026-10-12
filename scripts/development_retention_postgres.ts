import { SQL } from "bun";
const env=Bun.env;
let checks=0;
function check(ok:unknown,message:string){if(!ok)throw new Error(message);checks++;}
let db:SQL|undefined;
try {
 check(env.APP_ENV==="development" && env.NEON_DEV_ENDPOINT==="ep-withered-resonance-b59tusv3","Development only");
 const url=env.AXS_RETENTION_TEST_DATABASE_URL??"";
 check(new URL(url).hostname.startsWith("ep-rough-band-b53bn1u1"),"Isolated child only");
 db=new SQL(url,{max:3,connectionTimeout:15,idleTimeout:5});
 const role=(await db`SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user`)[0];
 check(!role.rolsuper&&!role.rolbypassrls,"Role bypasses RLS");
 const none=await db`SELECT visita_id FROM identity_retention`;
 check(none.length===0,"No tenant context must see no rows");
 await db.begin(async tx=>{
  await tx`SELECT set_config('app.tenant_id','axs_demo_condo_a',true)`;
  const a=await tx`SELECT visita_id FROM identity_retention`;
  check(a.length===1 && a[0].visita_id==="axs_retention_rls_a_20261012","A isolation");
  const cross=await tx`UPDATE identity_retention SET last_error='cross' WHERE condominio_id='axs_demo_condo_b' RETURNING visita_id`;
  check(cross.length===0,"Cross update not denied");
 });
 let rejected=false;
 try {
  await db.begin(async tx=>{
   await tx`SELECT set_config('app.tenant_id','axs_demo_condo_a',true)`;
   await tx`INSERT INTO identity_retention(visita_id,condominio_id,captura_id,policy_version,captured_at,base_at,expires_at,state,snapshots,audit_context,next_attempt_at) VALUES ('axs_retention_rls_b_20261012','axs_demo_condo_a','bad','test',now(),now(),now(),'active','[]','{}',now())`;
  });
 } catch(e) {rejected=(e as {errno?:string;code?:string}).errno==="42501" || (e as {code?:string}).code==="42501";}
 check(rejected,"Cross visit insert not denied by RLS");
 let ready!:()=>void,release!:()=>void;
 const taken=new Promise<void>(r=>ready=r), done=new Promise<void>(r=>release=r);
 const first=db.begin(async tx=>{
  await tx`SELECT set_config('app.tenant_id','axs_demo_condo_a',true)`;
  const rows=await tx`SELECT visita_id FROM identity_retention WHERE state='active' ORDER BY visita_id FOR UPDATE SKIP LOCKED`;
  check(rows.length===1,"First worker failed to lock");
  ready();
  await Promise.race([done,new Promise((_,rej)=>setTimeout(()=>rej(new Error("Barrier timeout")),15000))]);
  await tx`UPDATE identity_retention SET state='pending',operation_id='rls-operation',claim_token='rls-claim',claim_until=now()+interval '15 minutes' WHERE visita_id='axs_retention_rls_a_20261012'`;
 });
 try {
  await taken;
  await db.begin(async tx=>{
   await tx`SELECT set_config('app.tenant_id','axs_demo_condo_a',true)`;
   const rows=await tx`SELECT visita_id FROM identity_retention WHERE state='active' ORDER BY visita_id FOR UPDATE SKIP LOCKED`;
   check(rows.length===0,"Second worker took locked pair");
  });
 } finally {release();}
 await first;
 await db.begin(async tx=>{
  await tx`SELECT set_config('app.tenant_id','axs_demo_condo_a',true)`;
  const rows=await tx`SELECT visita_id FROM identity_retention WHERE state='pending' AND claim_until>now()`;
  check(rows.length===1,"Durable exclusive claim missing");
 });
 console.log("AXS_RETENTION_POSTGRES_RESULT "+JSON.stringify({status:"PASS",checks,branch:"br-small-poetry-b5fnlc9t",rls:true,role_without_bypass:true,skip_locked:true,concurrent_workers:2}));
} catch(e) { console.error("AXS_RETENTION_POSTGRES_RESULT "+JSON.stringify({status:"FAIL",checks,error:e instanceof Error?e.message.replace(/postgres(?:ql)?:\/\/\S+/g,"[redacted]"):"unknown"})); }
finally {await db?.close();}
