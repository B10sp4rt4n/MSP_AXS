"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ApiError } from "@/lib/api";

type Company = { tenant_id:string; nombre:string; msp_id:string; owner_user_id:string; modalidad:string; directorio_habilitado:boolean; privacy_contact:string; privacy_notice_version:string };
type Stage = "alta" | "capacidades" | "habilitar";
const empty = { nombre:"", msp_id:"", owner_user_id:"", privacy_contact:"", privacy_notice_url:"", privacy_notice_version:"" };
const field = "w-full rounded-lg border border-gray-700 bg-gray-800 p-3 text-white";
const label = "block text-sm text-gray-300 mb-1";
export default function CorporativoSuperadminClient() {
  const {getToken,isLoaded,userId}=useAuth();
  const [authorized,setAuthorized]=useState(false);
  const [checking,setChecking]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [result,setResult]=useState("");
  const [form,setForm]=useState(empty);
  const [requestId,setRequestId]=useState("");
  const [company,setCompany]=useState<Company|null>(null);
  const [stage,setStage]=useState<Stage>("alta");
  const [limits,setLimits]=useState({max_sedes:2,max_destinos_por_sede:10});
  const [confirmed,setConfirmed]=useState(false);
  const tokenRequired=useCallback(async()=>{const token=await getToken();if(!token)throw Error("Sesión caducada");return token},[getToken]);
  const check=useCallback(async()=>{
    setChecking(true);setAuthorized(false);setError("");
    try {
      await api.get<{authorized:boolean}>("/plataforma/corporativo/acceso",await tokenRequired());
      setAuthorized(true);
    } catch(e){
      setError(e instanceof ApiError && e.status===404 ? "La consola corporativa no está habilitada en este ambiente."
        : e instanceof ApiError && [401,403].includes(e.status) ? "Tu cuenta no tiene autoridad GLOBAL."
        : "No se pudo validar el acceso. No se ha efectuado ninguna operación.");
    } finally {setChecking(false)}
  },[tokenRequired]);
  useEffect(()=>{if(isLoaded&&userId)void check()},[isLoaded,userId,check]);
  const create=async()=>{
    if(Object.values(form).some(v=>!v.trim())){setError("Completa todos los datos, incluido el aviso de privacidad.");return}
    setBusy(true);setError("");setResult("");
    try {
      // Persistir ID antes de enviar permite reintentar sin duplicar empresa.
      const id=requestId||crypto.randomUUID();setRequestId(id);
      const created=await api.post<Company>("/plataforma/corporativo/empresas",{...form,request_id:id},await tokenRequired());
      setCompany(created);setStage("capacidades");
      setResult("Empresa creada sin habilitar. Configura capacidades.");
    }catch(e){setError(e instanceof Error?e.message:"No se pudo crear la empresa")}
    finally{setBusy(false)}
  };
  const configure=async()=>{
    if(!company)return;
    if(!Number.isInteger(limits.max_sedes)||limits.max_sedes<1||limits.max_sedes>1000||!Number.isInteger(limits.max_destinos_por_sede)||limits.max_destinos_por_sede<1||limits.max_destinos_por_sede>2000){
      setError("Sedes: 1 a 1000; destinos por sede: 1 a 2000.");return;
    }
    setBusy(true);setError("");setResult("");
    try {
      await api.put("/plataforma/corporativo/empresas/"+encodeURIComponent(company.tenant_id)+"/capacidades",limits,await tokenRequired());
      setStage("habilitar");setResult("Capacidades guardadas. El directorio sigue deshabilitado.");
    }catch(e){setError(e instanceof Error?e.message:"No se guardaron capacidades")}finally{setBusy(false)}
  };
  const activate=async()=>{
    if(!company||!confirmed)return;
    setBusy(true);setError("");setResult("");
    try{
      const updated=await api.post<Company>("/plataforma/corporativo/empresas/"+encodeURIComponent(company.tenant_id)+"/habilitar-directorio",{confirmacion:true},await tokenRequired());
      setCompany(updated);setResult("Directorio habilitado. No habilita visitantes, QR ni accesos físicos.");
    }catch(e){setError(e instanceof Error?e.message:"No se pudo habilitar directorio")}finally{setBusy(false)}
  };
  const reset=()=>{setForm(empty);setRequestId("");setCompany(null);setLimits({max_sedes:2,max_destinos_por_sede:10});setStage("alta");setConfirmed(false);setError("");setResult("")};
  return <main className="min-h-screen bg-gray-950 p-5 text-white md:p-8"><div className="mx-auto max-w-3xl">
    <a href="/dashboard/msp" className="text-sm text-blue-300">← Panel MSP</a>
    <header className="mt-4 mb-6"><h1 className="text-2xl font-semibold">AXS Corporativo · Superadmin</h1><p className="mt-2 text-gray-400">Alta y configuración de directorio empresarial. Sin movimientos de visitantes.</p></header>
    {checking&&<p role="status">Verificando acceso…</p>}
    {error&&<p role="alert" className="mb-4 rounded-lg border border-red-900 bg-red-950/50 p-3 text-red-200">{error}</p>}
    {!checking&&!authorized&&<button className="rounded-lg bg-gray-800 px-5 py-3" onClick={()=>void check()}>Reintentar comprobación</button>}
    {authorized&&!checking&&<>
      <div className="mb-5 flex flex-wrap gap-2 text-sm text-gray-300"><span className="rounded bg-gray-800 px-3 py-2">1 · Empresa</span><span className="rounded bg-gray-800 px-3 py-2">2 · Capacidades</span><span className="rounded bg-gray-800 px-3 py-2">3 · Habilitación</span></div>
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
        ] as const).map(([key,title])=><div key={key}><label htmlFor={key} className={label}>{title}</label><input id={key} className={field} required type={key==="privacy_contact"?"email":key==="privacy_notice_url"?"url":"text"} value={form[key]} onChange={e=>{setForm(v=>({...v,[key]:e.target.value}));setRequestId("")}} /></div>)}
        <button disabled={busy} onClick={()=>void create()} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50">{busy?"Guardando…":"Crear empresa deshabilitada"}</button>
      </section>}
      {stage==="capacidades"&&<section className="space-y-4 rounded-xl border border-gray-700 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold">Capacidades de directorio</h2>
        {(["max_sedes","max_destinos_por_sede"] as const).map(key=><div key={key}><label className={label} htmlFor={key}>{key==="max_sedes"?"Máximo de sedes":"Destinos máximos por sede"}</label><input id={key} type="number" min={1} max={key==="max_sedes"?1000:2000} value={limits[key]} onChange={e=>setLimits(v=>({...v,[key]:Number(e.target.value)}))} className={field}/></div>)}
        <button disabled={busy} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50" onClick={()=>void configure()}>{busy?"Guardando…":"Guardar capacidades"}</button>
      </section>}
      {stage==="habilitar"&&<section className="space-y-4 rounded-xl border border-gray-700 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold">Habilitación del directorio</h2>
        <p className="text-sm text-gray-300">Verifica que el aviso de privacidad, el owner y las políticas estén correctos. Esta acción no habilita el ingreso de visitantes.</p>
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1 h-5 w-5" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Confirmo habilitar exclusivamente el directorio corporativo de esta empresa.</span></label>
        <button disabled={busy||!confirmed||!!company?.directorio_habilitado} className="w-full rounded-lg bg-blue-600 p-3 font-semibold disabled:opacity-50" onClick={()=>void activate()}>{company?.directorio_habilitado?"Directorio habilitado":busy?"Habilitando…":"Habilitar directorio"}</button>
      </section>}
      {result&&<p role="status" className="mt-4 rounded-lg border border-gray-700 bg-gray-900 p-3 text-sm">{result}</p>}
      <button className="mt-6 rounded-lg border border-gray-600 px-4 py-2 text-sm" onClick={reset}>Comenzar otra alta</button>
    </>}
  </div></main>;
}
