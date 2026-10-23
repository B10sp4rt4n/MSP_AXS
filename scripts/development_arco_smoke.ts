// One-shot synthetic Development only. Tokens and private content never logged.
import { createHmac } from 'node:crypto';
const API='https://axs-development-backend-production.up.railway.app';
const env=process.env;
if(env.APP_ENV!=='development'||env.NEON_DEV_ENDPOINT!=='ep-withered-resonance-b59tusv3'||!env.AXS_TEST_SECRET)throw Error('Development configuration required');
let checks=0;
function token(actor:string){
 const enc=(v:object)=>Buffer.from(JSON.stringify(v)).toString('base64url');const now=Math.floor(Date.now()/1000);
 const body=enc({alg:'HS256',typ:'JWT'})+'.'+enc({sub:actor,role:'MSP_ADMIN',method:'local',iat:now,exp:now+300});
 return body+'.'+createHmac('sha256',env.AXS_TEST_SECRET!).update(body).digest('base64url');
}
async function req(actor:string|null,path:string,status:number,body?:object){
 const r=await fetch(API+path,{method:body?'POST':'GET',redirect:'error',signal:AbortSignal.timeout(30000),headers:{...(actor?{Authorization:`Bearer ${token(actor)}`} :{}),'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
 checks++;if(r.status!==status)throw Error(`check ${checks}: HTTP ${r.status}; expected ${status}`);
 return r.json();
}
try{
 if(env.AXS_ARCO_SMOKE_PHASE==='closed'){
  for(const side of ['a','b'])await req(`axs_demo_admin_${side}`,`/arco/axs_demo_condo_${side}`,404);
  console.log('AXS_ARCO_SMOKE_RESULT '+JSON.stringify({status:'PASS',phase:'closed',checks,synthetic_only:true,authenticated_api_disabled:true}));
 }else{
 const proof=[];
 for(const side of ['a','b']){
  const tenant=`axs_demo_condo_${side}`,actor=`axs_demo_admin_${side}`,other=`axs_demo_admin_${side==='a'?'b':'a'}`;
  const id=side==='a'?'ac000001-0000-4000-8000-000000000001':'ac000001-0000-4000-8000-000000000002';
  const path=`/arco/${tenant}`;
  await req(null,path,401);await req(other,path,403);
  const body={request_id:id,received_at:'2026-10-22T12:00:00Z',determination_due:'2026-11-20T18:00:00Z',right:'cancelacion',subject_ref:'ARCO_SIM_002_'+side,owner_id:actor};
  let row=await req(actor,path,200);row=row.find((r:any)=>r.case_id===id);
  if(!row){row=await req(actor,path,200,body);await req(actor,path,200,body);}
  await req(other,path+'/'+id+'/estado',403,{version:row.version,state:'verificada',reference:'SYNTHETIC_DENIED'});
  const states=['recibida','verificada','resuelta','ejecutando','cerrada'];
  while(row.state!=='cerrada'){
   const next=states[states.indexOf(row.state)+1];if(!next)throw Error('Unknown state');
   if(next==='cerrada')await req(actor,path+'/'+id+'/estado',422,{version:row.version,state:next,reference:'SYNTHETIC_CLOSE',pending_actions:1,communication_ref:'SYNTHETIC_REPLY'});
   const data:any={version:row.version,state:next,reference:'SYNTHETIC_'+next,pending_actions:next==='cerrada'?0:1};
   if(next==='resuelta')Object.assign(data,{outcome:'procedente',communication_ref:'SYNTHETIC_DECISION',execution_due:'2026-12-01T18:00:00Z'});
   if(next==='cerrada')data.communication_ref='SYNTHETIC_REPLY';
   row=await req(actor,path+'/'+id+'/estado',200,data);
   await req(actor,path+'/'+id+'/estado',409,data);
  }
  const rows=await req(actor,path,200);if(rows.filter((r:any)=>r.case_id===id).length!==1||row.pending_actions!==0||row.history.length!==4)throw Error('Dossier invariant failed');
  proof.push({tenant,case_id:id,state:row.state,history_count:row.history.length});
 }
 console.log('AXS_ARCO_SMOKE_RESULT '+JSON.stringify({status:'PASS',synthetic_only:true,checks,proof,identity:'existing local test actors; not real Clerk sessions',execution:'tracking only; no deletion or outbound mail'}));
}
}catch(e){console.log('AXS_ARCO_SMOKE_RESULT '+JSON.stringify({status:'FAIL',checks,error:e instanceof Error?e.message:'unknown'}));process.exitCode=1;}
