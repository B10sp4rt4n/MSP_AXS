"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Visita } from "@/lib/types";
import { horaPresencia, instante, resumirPresencia } from "@/lib/presencia";

type Props = { condominioId: string; residente?: boolean };
export default function PresenciaVisitas({ condominioId, residente = false }: Props) {
  const { getToken } = useAuth();
  const [revision, setRevision] = useState(0);
  const [resultado, setResultado] = useState<{ clave: string; visitas: Visita[]; fecha: number } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const clave = `${residente ? "mis-visitas" : "condominio"}/${condominioId}`;
  useEffect(() => {
    let activo = true;
    setLoading(true); setError(""); setResultado(null);
    if (!condominioId) return () => { activo = false; };
    getToken().then(async token => {
      if (!token) throw new Error("Tu sesión no está disponible. Vuelve a iniciar sesión.");
      const visitas = await api.get<Visita[]>(`/visitas/${clave}`, token);
      if (activo) setResultado({ clave, visitas, fecha: Date.now() });
    }).catch(e => { if (activo) setError(e instanceof Error ? e.message : "No se pudo consultar la presencia."); })
      .finally(() => { if (activo) setLoading(false); });
    return () => { activo = false; };
  }, [clave, condominioId, getToken, revision]);
  const datos = resultado?.clave === clave ? resultado : null;
  const resumen = datos ? resumirPresencia(datos.visitas, datos.fecha) : null;
  return <section aria-label="Presencia de visitas" className="mb-6 rounded-xl border border-purple-700 bg-gray-900 p-4">
    <div className="flex items-center justify-between gap-3">
      <h2 className="font-semibold text-lg">¿Quién sigue dentro?</h2>
      <button onClick={() => setRevision(v => v + 1)} className="text-sm text-purple-300 hover:underline">Actualizar presencia</button>
    </div>
    <p className="text-xs text-gray-400 mt-2">{residente ? "Visitas de tu vivienda" : "Visitas del condominio"} con entrada y sin salida registrada. No confirma presencia física en tiempo real.</p>
    {error ? <p role="alert" className="mt-4 text-red-300">{error}</p> : loading || !resumen || !datos ? <p role="status" className="mt-4 text-gray-400">Consultando presencia…</p> : <>
      <dl className="grid grid-cols-3 gap-2 my-4">
        {[["Sin salida", resumen.dentro.length], ["Entradas hoy", resumen.entradasHoy], ["Salidas hoy", resumen.salidasHoy]].map(([label, value]) => <div key={label} className="rounded-lg bg-gray-800 p-3"><dt className="text-xs text-gray-300">{label}</dt><dd className="text-2xl font-semibold">{value}</dd></div>)}
      </dl>
      <p className="text-xs text-gray-400">Actualizado: {horaPresencia(new Date(datos.fecha).toISOString())}. Hora de Ciudad de México.</p>
      {resumen.ultimo && <p className="text-sm mt-3">Último movimiento: {resumen.ultimo.tipo} de <strong>{resumen.ultimo.visita.nombre_visitante}</strong> · {horaPresencia(resumen.ultimo.fecha)}</p>}
      {resumen.dentro.length === 0 ? <p className="mt-4 text-gray-300">No hay visitas con entrada y sin salida registrada.</p> : <ul className="mt-4 space-y-3">
        {resumen.dentro.map(v => <li key={v.visita_id} className="border-t border-gray-700 pt-3">
          <p className="font-medium">{v.nombre_visitante}{!residente && <span className="text-sm text-gray-400"> · {v.casa_unidad}</span>}</p>
          <p className="text-sm text-gray-300">Entrada: {horaPresencia(v.entrada_registrada_en!)}</p>
          {datos.fecha - instante(v.entrada_registrada_en)! >= 86400000 && <p className="text-xs text-amber-300 mt-1">Más de 24 horas sin salida registrada. Conviene revisar el registro con vigilancia.</p>}
        </li>)}
      </ul>}
      {resumen.revisar.length > 0 && <details className="mt-4 rounded-lg border border-amber-700 p-3 text-amber-200"><summary>{resumen.revisar.length} registros por revisar · excluidos de los indicadores</summary><ul className="mt-2 text-sm">{resumen.revisar.map(v => <li key={v.visita_id}>{v.nombre_visitante}: estado y fechas no coinciden.</li>)}</ul></details>}
    </>}
  </section>;
}
