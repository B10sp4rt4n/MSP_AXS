"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export type ResidenteIncorporacion = {
  usuario_id: string; nombre: string; email: string; rol: string; casa_unidad: string | null;
  incorporacion?: { estado: string; registro_completo: boolean; vivienda_valida: boolean; puede_invitar: boolean;
    invitacion: { estado: string; solicitada_en: string | null; vence_en: string | null } } | null;
};
const labels: Record<string,string> = {precargado:"Precargado",registrado:"Registrado",vivienda_pendiente:"Vivienda pendiente",
  invitacion_solicitada:"Invitación solicitada",invitacion_vencida:"Invitación vencida",revisar_invitacion:"Revisar invitación"};
type Receipt = { email: string; message: string };
export default function IncorporacionResidentes({usuarios,condominioId,getToken,onRefresh,loading}: {
  usuarios: ResidenteIncorporacion[]; condominioId:string; getToken:()=>Promise<string|null>; onRefresh:()=>void; loading:boolean;
}) {
  const [query,setQuery]=useState(""); const [filter,setFilter]=useState("");
  const [selected,setSelected]=useState<string[]>([]); const [review,setReview]=useState<ResidenteIncorporacion[]>([]);
  const [busy,setBusy]=useState(false); const [receipts,setReceipts]=useState<Receipt[]>([]);
  const active=useRef(true); const running=useRef(false);
  useEffect(()=>{active.current=true;return()=>{active.current=false};},[]);
  const residents=usuarios.filter(u=>u.rol==="RESIDENTE");
  const visible=residents.filter(u=>(!filter||u.incorporacion?.estado===filter)&&
    `${u.nombre} ${u.email} ${u.casa_unidad??""}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const eligible=usuarios.filter(u=>selected.includes(u.usuario_id)&&u.incorporacion?.puede_invitar);
  async function enviar(){
    if(running.current||!review.length)return;
    running.current=true;setBusy(true);setReceipts([]);
    const results:Receipt[]=[];
    try{
      for(let index=0;index<review.length;index++){
        if(!active.current)break;
        const u=review[index];
        try{
          const token=await getToken(); if(!active.current)break;
          if(!token)throw Error("Inicia sesión nuevamente");
          await api.post(`/condominios/${encodeURIComponent(condominioId)}/usuarios/${encodeURIComponent(u.usuario_id)}/invitacion`,
            {expected_email:u.email},token);
          results.push({email:u.email,message:"Clerk aceptó la solicitud de envío"});
        }catch(e){
          results.push({email:u.email,message:e instanceof Error?e.message:"Resultado incierto; revisa antes de reintentar"});
          results.push(...review.slice(index+1).map(p=>({email:p.email,message:"No intentado: lote detenido"})));
          break;
        }
        if(active.current)setReceipts([...results]);
      }
    }finally{
      running.current=false;
      if(active.current){setReceipts(results);setBusy(false);setReview([]);setSelected([]);onRefresh();}
    }
  }
  return <section aria-label="Incorporación de residentes" className="border border-gray-700 rounded-xl p-4 mb-5 space-y-3">
    <h3 className="font-semibold">Incorporación de residentes</h3>
    <div className="flex flex-wrap gap-4 text-sm" role="status">
      <span>{residents.length} residentes</span><span>{residents.filter(u=>u.incorporacion?.registro_completo).length} registrados</span>
      <span>{residents.filter(u=>u.incorporacion&&!u.incorporacion.registro_completo).length} pendientes de registro</span>
      <span>{residents.filter(u=>u.incorporacion&&!u.incorporacion.vivienda_valida).length} sin vivienda válida</span>
    </div>
    <p className="text-xs text-gray-400">Una solicitud aceptada por Clerk no confirma entrega del correo. Los pendientes de vivienda pueden coincidir con registrados o pendientes de registro.</p>
    <label className="block text-sm">Buscar residente<input disabled={busy||review.length>0} className="block w-full bg-gray-800 p-2 rounded" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nombre, correo o vivienda" /></label>
    <label className="block text-sm">Estado de incorporación<select disabled={busy||review.length>0} value={filter} onChange={e=>{setFilter(e.target.value);setSelected([]);}} className="block bg-gray-800 p-2 rounded">
      <option value="">Todos</option>{Object.entries(labels).map(([value,label])=><option key={value} value={value}>{label}</option>)}
    </select></label>
    <p className="text-sm">{eligible.length} seleccionados. Máximo 20 por envío.</p>
    <div className="max-h-80 overflow-auto space-y-2">{visible.map(u=><label key={u.usuario_id} className="flex gap-3 border-t border-gray-700 py-2">
      <input type="checkbox" checked={selected.includes(u.usuario_id)} disabled={busy||loading||review.length>0||!u.incorporacion?.puede_invitar||(!selected.includes(u.usuario_id)&&selected.length>=20)}
        onChange={e=>setSelected(old=>e.target.checked?[...old,u.usuario_id]:old.filter(id=>id!==u.usuario_id))} />
      <span>{u.nombre} · {u.email}<span className="block text-xs text-gray-400">{u.casa_unidad??"Sin vivienda"} · {labels[u.incorporacion?.estado??""]??"Actualiza para consultar estado"}</span></span>
    </label>)}</div>
    {!visible.length&&<p className="text-sm">{loading?"Actualizando…":"Sin residentes para este filtro"}</p>}
    {!review.length&&<button disabled={busy||loading||!eligible.length} onClick={()=>{setReview(eligible);setReceipts([]);}} className="bg-blue-600 px-4 py-2 rounded disabled:opacity-50">Revisar invitaciones seleccionadas</button>}
    {review.length>0&&<div className="border border-blue-700 p-3 rounded space-y-2">
      <h4>Confirmar destinatarios ({review.length})</h4>
      <ul>{review.map(u=><li key={u.usuario_id}>{u.nombre} — {u.email}</li>)}</ul>
      <p className="text-sm">Se enviará una invitación de registro a cada correo. Si sales de este condominio se detendrán los envíos aún no iniciados.</p>
      <button disabled={busy||loading} onClick={enviar} className="bg-green-700 px-4 py-2 rounded disabled:opacity-50">{busy?"Enviando…":"Confirmar y enviar invitaciones"}</button>
      <button disabled={busy} onClick={()=>setReview([])} className="ml-3">Cancelar</button>
    </div>}
    {receipts.length>0&&<div aria-live="polite"><h4>Resultado por destinatario</h4><ul>{receipts.map(r=><li key={r.email} className="text-sm">{r.email}: {r.message}</li>)}</ul></div>}
  </section>;
}
