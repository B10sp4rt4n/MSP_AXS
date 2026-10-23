"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ApiError } from "@/lib/api";

type Limits = { max_sedes:number; max_destinos_por_sede:number };
type CapacityRequest = Limits & { request_id:string; expected_revision:number };
type CapacityOperation = CapacityRequest & { estado:"pending"|"confirmed"|"needs_review"; revision:number };
type CapacityConfirmation = { request_id:string; estado:"confirmed"; tenant_id:string; cuotas:Limits; revision:number };
type Company = { tenant_id:string; nombre:string; msp_id:string; owner_user_id:string; modalidad:string; directorio_habilitado:boolean; privacy_contact:string; privacy_notice_version:string; capacidades?:{max_sedes:number|null;max_destinos_por_sede:number|null}; capacidades_operacion?:CapacityOperation|null; capacidades_confirmadas?:boolean; capacidades_revision?:number };
type Stage = "alta" | "capacidades" | "habilitar";
const empty = { nombre:"", msp_id:"", owner_user_id:"", privacy_contact:"", privacy_notice_url:"", privacy_notice_version:"" };
const field = "w-full rounded-lg border border-gray-700 bg-gray-800 p-3 text-white";
const label = "block text-sm text-gray-300 mb-1";
export default function CorporativoSuperadminClient() {
  const {getToken,isLoaded,userId}=useAuth();
  const [authorized,setAuthorized]=useState(false);
  const [credentialsReady,setCredentialsReady]=useState(false);
  const [ownerChecked,setOwnerChecked]=useState("");
  const [lookupId,setLookupId]=useState("");
  const [checking,setChecking]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [result,setResult]=useState("");
  const [form,setForm]=useState(empty);
  const [requestId,setRequestId]=useState("");
  const [company,setCompany]=useState<Company|null>(null);
  const [stage,setStage]=useState<Stage>("alta");
  const [limits,setLimits]=useState({max_sedes:2,max_destinos_por_sede:10});
  const [capacityRequest,setCapacityRequest]=useState<CapacityRequest|null>(null);
  const [confirmed,setConfirmed]=useState(false);
  const capacityNeedsReview=company?.capacidades_operacion?.estado==="needs_review";
  const tokenRequired=useCallback(async()=>{const token=await getToken();if(!token)throw Error("Sesión caducada");return token},[getToken]);
  const check=useCallback(async()=>{
    setChecking(true);setAuthorized(false);setCredentialsReady(false);setError("");
    try {
      const access=await api.get<{authorized:boolean;provisioning_enabled:boolean;credencial_configurada:boolean}>(
        "/plataforma/corporativo/acceso",await tokenRequired());
      if(access.authorized!==true||access.provisioning_enabled!==true)throw Error("Autoridad no confirmada");
      setCredentialsReady(access.credencial_configurada===true);
      setAuthorized(true);
    } catch(e){
      setError(e instanceof ApiError && e.status===404 ? "La consola corporativa no está habilitada en este ambiente."
        : e instanceof ApiError && [401,403].includes(e.status) ? "Tu cuenta no tiene autoridad GLOBAL."
        : "No se pudo validar el acceso. No se ha efectuado ninguna operación.");
    } finally {setChecking(false)}
  },[tokenRequired]);
  useEffect(()=>{if(isLoaded&&userId)void check()},[isLoaded,userId,check]);
  const verifyOwner=async()=>{
    if(!form.owner_user_id.trim())return setError("Indica el ID del owner.");
    setError("");setOwnerChecked("");
    try {
      const person=await api.get<{usuario_id:string}>(
        "/plataforma/corporativo/usuarios/"+encodeURIComponent(form.owner_user_id.trim()),await tokenRequired());
      if(person.usuario_id!==form.owner_user_id.trim())throw Error("Identidad no coincide");
      setOwnerChecked(person.usuario_id);
    }catch(e){setError(e instanceof Error?e.message:"No se pudo verificar al owner")}
  };
  const loadCompany=async()=>{
    const id=lookupId.trim();
    if(!/^corp_[a-f0-9]{32}$/.test(id))return setError("Indica un identificador corporativo válido.");
    if(capacityRequest&&!capacityNeedsReview&&company?.tenant_id!==id)return setError("Concilia primero las capacidades pendientes de esta empresa.");
    setBusy(true);setError("");setResult("");
    try{
      const known=await api.get<Company>("/plataforma/corporativo/empresas/"+encodeURIComponent(id),await tokenRequired());
      setCompany(known);setRequestId("");setOwnerChecked("");setConfirmed(false);
      const operation=known.capacidades_operacion;
      // CORE conserva el intento incluso si el navegador perdió toda su memoria.
      // Si aún no llegó a CORE, una consulta tampoco debe descartar el UUID local.
      const needsReview=operation?.estado==="needs_review";
      const pending=operation&&(operation.estado==="pending"||needsReview)?{
        request_id:operation.request_id,expected_revision:operation.expected_revision,max_sedes:operation.max_sedes,
        max_destinos_por_sede:operation.max_destinos_por_sede
      }:!operation&&company?.tenant_id===id?capacityRequest:null;
      setCapacityRequest(pending);
      setLimits(pending?{max_sedes:pending.max_sedes,max_destinos_por_sede:pending.max_destinos_por_sede}
        :{max_sedes:known.capacidades?.max_sedes??2,max_destinos_por_sede:known.capacidades?.max_destinos_por_sede??10});
      const ready=!pending&&!needsReview&&known.capacidades_confirmadas===true;
      setStage(ready?"habilitar":"capacidades");
      setResult(needsReview?"La conciliación requiere revisión por cambios en GOV. Guardar capacidades y habilitar permanecen bloqueados; no se creará otra operación."
        :pending?"Conciliación de capacidades pendiente. Reintenta con la misma referencia y cuotas; la habilitación sigue bloqueada."
        :ready?"Capacidades confirmadas en CORE y GOV. Revisa antes de operar."
        :"Las cuotas no están confirmadas en CORE y GOV. Guarda capacidades explícitamente antes de habilitar.");
    }catch(e){setError(e instanceof Error?e.message:"No se pudo recuperar la empresa")}
    finally{setBusy(false)}
  };
  const create=async()=>{
    if(!credentialsReady){setError("Credencial segregada no configurada. Operación bloqueada.");return}
    if(Object.values(form).some(v=>!v.trim())){setError("Completa todos los datos, incluido el aviso de privacidad.");return}
    if(ownerChecked!==form.owner_user_id.trim()){setError("Verifica primero la identidad del owner.");return}
    setBusy(true);setError("");setResult("");
    try {
      // Persistir ID antes de enviar permite reintentar sin duplicar empresa.
      const id=requestId||crypto.randomUUID();setRequestId(id);
      const created=await api.post<Company>("/plataforma/corporativo/empresas",{...form,request_id:id},await tokenRequired());
      setCompany(created);setLookupId(created.tenant_id);setCapacityRequest(null);setStage("capacidades");
      setResult("Empresa creada sin habilitar. Configura capacidades.");
    }catch(e){setError((e instanceof Error?e.message:"Resultado incierto")
      +". Conserva la referencia del alta y reintenta sin cambiar los datos, o consulta la empresa mediante su ID.")}
    finally{setBusy(false)}
  };
  const configure=async()=>{
    if(!company||!credentialsReady||busy||capacityNeedsReview)return;
    const requested=capacityRequest??{...limits,request_id:crypto.randomUUID(),expected_revision:company.capacidades_revision??0};
    if(!Number.isInteger(requested.max_sedes)||requested.max_sedes<1||requested.max_sedes>1000||!Number.isInteger(requested.max_destinos_por_sede)||requested.max_destinos_por_sede<1||requested.max_destinos_por_sede>2000){
      setError("Sedes: 1 a 1000; destinos por sede: 1 a 2000.");return;
    }
    // Congelar UUID y payload antes del envío; un fallo no demuestra que no se guardó.
    setCapacityRequest(requested);setConfirmed(false);
    setBusy(true);setError("");setResult("");
    try {
      const saved=await api.put<CapacityConfirmation>("/plataforma/corporativo/empresas/"+encodeURIComponent(company.tenant_id)+"/capacidades",requested,await tokenRequired());
      if(saved.estado!=="confirmed"||saved.request_id!==requested.request_id||saved.tenant_id!==company.tenant_id||saved.revision!==requested.expected_revision+1||
        saved.cuotas?.max_sedes!==requested.max_sedes||saved.cuotas?.max_destinos_por_sede!==requested.max_destinos_por_sede)
        throw Error("La operación de capacidades no está confirmada");
      const current=await api.get<Company>("/plataforma/corporativo/empresas/"+encodeURIComponent(company.tenant_id),await tokenRequired());
      setCompany(current);
      if(current.capacidades_confirmadas!==true||current.capacidades_operacion?.estado!=="confirmed"||
         current.capacidades_operacion.request_id!==requested.request_id||
         current.capacidades_operacion.expected_revision!==requested.expected_revision||
         current.capacidades_operacion.revision!==saved.revision||current.capacidades_revision!==saved.revision||
         current.capacidades_operacion.max_sedes!==requested.max_sedes||
         current.capacidades_operacion.max_destinos_por_sede!==requested.max_destinos_por_sede||
         current.capacidades?.max_sedes!==requested.max_sedes||
         current.capacidades?.max_destinos_por_sede!==requested.max_destinos_por_sede)
        throw Error("Las capacidades no aparecen confirmadas en CORE y GOV");
      setCapacityRequest(null);setStage("habilitar");
      setResult("Capacidades confirmadas en CORE y GOV. Revisa la habilitación del directorio por separado.");
    }catch(e){setError((e instanceof Error?e.message:"Resultado incierto")
      +". Conciliación pendiente: conserva la referencia y reintenta las mismas cuotas, o consulta el estado de esta empresa.")}
    finally{setBusy(false)}
  };
  const activate=async()=>{
    if(!company||!confirmed||!credentialsReady||company.directorio_habilitado||company.capacidades_confirmadas!==true||capacityRequest||capacityNeedsReview)return;
    setBusy(true);setError("");setResult("");
    try{
      const updated=await api.post<Company>("/plataforma/corporativo/empresas/"+encodeURIComponent(company.tenant_id)+"/habilitar-directorio",{confirmacion:true},await tokenRequired());
      const current=await api.get<Company>("/plataforma/corporativo/empresas/"+encodeURIComponent(updated.tenant_id),await tokenRequired());
      setCompany(current);
      if(current.directorio_habilitado!==true)throw Error("La habilitación no está confirmada en CORE");
      setResult("Directorio confirmado como habilitado. No habilita visitantes, QR ni accesos físicos.");
    }catch(e){setError(e instanceof Error?e.message:"No se pudo habilitar directorio")}finally{setBusy(false)}
  };
  const reset=()=>{if(busy||(capacityRequest&&!capacityNeedsReview))return;setForm(empty);setRequestId("");setCapacityRequest(null);setCompany(null);setLookupId("");setOwnerChecked("");setLimits({max_sedes:2,max_destinos_por_sede:10});setStage("alta");setConfirmed(false);setError("");setResult("")};
  return <main className="min-h-screen bg-gray-950 p-5 text-white md:p-8"><div className="mx-auto max-w-3xl">
    <a href="/dashboard/msp" className="text-sm text-blue-300">← Panel MSP</a>
    <header className="mt-4 mb-6"><h1 className="text-2xl font-semibold">AXS Corporativo · Superadmin</h1><p className="mt-2 text-gray-400">Alta y configuración de directorio empresarial. Sin movimientos de visitantes.</p></header>
    {checking&&<p role="status">Verificando acceso…</p>}
    {authorized&&!credentialsReady&&<p role="alert">Falta configurar la credencial segregada: se bloquean las escrituras corporativas.</p>}
    {error&&<p role="alert" className="mb-4 rounded-lg border border-red-900 bg-red-950/50 p-3 text-red-200">{error}</p>}
    {!checking&&!authorized&&<button className="rounded-lg bg-gray-800 px-5 py-3" onClick={()=>void check()}>Reintentar comprobación</button>}
    {authorized&&!checking&&<>
      <div className="mb-5 flex flex-wrap gap-2 text-sm text-gray-300"><span className="rounded bg-gray-800 px-3 py-2">1 · Empresa</span><span className="rounded bg-gray-800 px-3 py-2">2 · Capacidades</span><span className="rounded bg-gray-800 px-3 py-2">3 · Habilitación</span></div>
      <section className="mb-5 rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-2">
        <h2 className="font-semibold">Retomar empresa existente</h2>
        <p className="text-sm text-gray-400">Utiliza el identificador corp_… para verificar el resultado de un alta o de cuotas con respuesta incierta.</p>
        <label htmlFor="corporate-lookup" className={label}>Identificador corporativo</label>
        <input id="corporate-lookup" className={field} value={lookupId}
          onChange={e=>setLookupId(e.target.value)} disabled={busy}/>
        <button className="rounded-lg border border-blue-600 px-4 py-2 disabled:opacity-50"
          disabled={busy} onClick={()=>void loadCompany()}>Consultar estado de empresa</button>
      </section>
      {requestId&&!company&&<p className="mb-4 text-sm text-amber-200 break-all">
        Referencia de alta pendiente: {requestId} · ID de consulta: corp_{requestId.replaceAll("-","")}
      </p>}
      {company&&<section className="mb-5 rounded-xl border border-gray-700 bg-gray-900 p-4">
        <h2 className="font-semibold">{company.nombre}</h2><p className="mt-1 break-all text-xs text-gray-400">{company.tenant_id}</p>
        <p className="mt-2 text-sm">{company.directorio_habilitado?"Directorio habilitado":"Directorio sin habilitar"} · Owner: {company.owner_user_id}</p>
      </section>}
      {stage==="alta"&&<section className="space-y-4 rounded-xl border border-gray-700 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold">Nueva empresa</h2>
        <p className="text-sm text-gray-400">El propietario debe ser un usuario AXS existente. No se crea una cuenta Clerk ni se envía una invitación.</p>
        {([
          ["nombre","Nombre de empresa"],["msp_id","ID del MSP responsable"],["owner_user_id","ID del propietario inicial"],
          ["privacy_contact","Correo del responsable de privacidad"],["privacy_notice_url","URL HTTPS del aviso de privacidad"],
          ["privacy_notice_version","Versión del aviso"]
        ] as const).map(([key,title])=><div key={key}><label htmlFor={key} className={label}>{title}</label><input id={key} className={field} required type={key==="privacy_contact"?"email":key==="privacy_notice_url"?"url":"text"} value={form[key]} disabled={busy||!!requestId} onChange={e=>{setForm(v=>({...v,[key]:e.target.value}));setOwnerChecked("");}} /></div>)}
        <button disabled={busy||!!requestId} type="button" onClick={()=>void verifyOwner()}
          className="rounded-lg border border-gray-600 px-4 py-2 disabled:opacity-50">
          Verificar owner existente</button>
        {ownerChecked&&<p role="status" className="text-sm">Owner verificado: {ownerChecked}</p>}
        <button disabled={busy||!credentialsReady} onClick={()=>void create()} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50">{busy?"Guardando…":"Crear empresa deshabilitada"}</button>
      </section>}
      {stage==="capacidades"&&<section className="space-y-4 rounded-xl border border-gray-700 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold">Capacidades de directorio</h2>
        {capacityRequest&&<p role="status" className="text-sm text-amber-200 break-all">Referencia de capacidades {capacityNeedsReview?"en revisión":"pendiente"}: {capacityRequest.request_id}. Las cuotas permanecen bloqueadas hasta conciliar el resultado.</p>}
        {(["max_sedes","max_destinos_por_sede"] as const).map(key=><div key={key}><label className={label} htmlFor={key}>{key==="max_sedes"?"Máximo de sedes":"Destinos máximos por sede"}</label><input id={key} type="number" min={1} max={key==="max_sedes"?1000:2000} value={limits[key]} disabled={busy||!!capacityRequest||capacityNeedsReview} onChange={e=>setLimits(v=>({...v,[key]:Number(e.target.value)}))} className={field}/></div>)}
        <button disabled={busy||!credentialsReady||capacityNeedsReview} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50" onClick={()=>void configure()}>{busy?"Guardando…":capacityNeedsReview?"Revisión requerida":capacityRequest?"Reintentar conciliación":"Guardar capacidades"}</button>
      </section>}
      {stage==="habilitar"&&<section className="space-y-4 rounded-xl border border-gray-700 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold">Habilitación del directorio</h2>
        <p className="text-sm text-gray-300">Verifica que el aviso de privacidad, el owner y las políticas estén correctos. Esta acción no habilita el ingreso de visitantes.</p>
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1 h-5 w-5" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Confirmo habilitar exclusivamente el directorio corporativo de esta empresa.</span></label>
        <button disabled={busy||!confirmed||!credentialsReady||!!company?.directorio_habilitado||company?.capacidades_confirmadas!==true||!!capacityRequest||capacityNeedsReview} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50" onClick={()=>void activate()}>{company?.directorio_habilitado?"Directorio habilitado":busy?"Habilitando…":"Habilitar directorio"}</button>
      </section>}
      {result&&<p role="status" className="mt-4 rounded-lg border border-gray-700 bg-gray-900 p-3 text-sm">{result}</p>}
      <button className="mt-6 rounded-lg border border-gray-600 px-4 py-2 text-sm" onClick={reset} disabled={busy||(!!capacityRequest&&!capacityNeedsReview)}>Comenzar otra alta</button>
    </>}
  </div></main>;
}
