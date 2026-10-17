"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Visita } from "@/lib/types";
import { horaPresencia, instante, resumirPresencia } from "@/lib/presencia";

type Props = { condominioId: string; residente?: boolean };
export default function PresenciaVisitas({ condominioId, residente = false }: Props) {
  const { getToken } = useAuth();
  const [seleccion, setSeleccion] = useState<"dentro" | "entradas" | "salidas" | null>(null);
  const detalleId = useId();
  const sectionRef = useRef<HTMLElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (!seleccion) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !sectionRef.current?.contains(event.target)) setSeleccion(null);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSeleccion(null);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [seleccion]);
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
  const tarjetas = resumen ? [
    { tone: "text-[#A7F3D0] border-emerald-400/40 bg-[radial-gradient(ellipse_at_top_left,rgba(16,185,129,0.30),rgba(17,24,39,0.85))] hover:border-emerald-300", id: "dentro" as const, label: "Dentro", visitas: resumen.dentro },
    { tone: "text-[#E5F99B] border-purple-400/40 bg-[radial-gradient(ellipse_at_top_left,rgba(229,255,0,0.20),rgba(139,44,255,0.28),rgba(17,24,39,0.85))] hover:border-purple-300", id: "entradas" as const, label: "Entradas hoy", visitas: resumen.entradas },
    { tone: "text-[#FFB4A8] border-red-400/40 bg-[radial-gradient(ellipse_at_top_left,rgba(239,68,68,0.30),rgba(17,24,39,0.85))] hover:border-red-300", id: "salidas" as const, label: "Salidas hoy", visitas: resumen.salidas },
  ] : [];
  const actual = tarjetas.find(t => t.id === seleccion);
  return <section ref={sectionRef} aria-label="Presencia de visitas" className="mb-6 rounded-xl border border-purple-700 bg-gray-900 p-4">
    <div className="flex items-center justify-between gap-3">
      <h2 className="font-semibold text-lg">¿Quién sigue dentro?</h2>
      <button onClick={() => setRevision(v => v + 1)} className="text-sm text-purple-300 hover:underline">Actualizar presencia</button>
    </div>
    <p className="text-xs text-gray-400 mt-2">{residente ? "Visitas de tu vivienda" : "Visitas del condominio"} con entrada y sin salida registrada. No confirma presencia física en tiempo real.</p>
    {error ? <p role="alert" className="mt-4 text-red-300">{error}</p> : loading || !resumen || !datos ? <p role="status" className="mt-4 text-gray-400">Consultando presencia…</p> : <>
      <div className="grid grid-cols-3 gap-2 my-4" aria-label="Filtrar visitas por estado">
        {tarjetas.map(t => <button key={t.id} type="button" aria-expanded={seleccion === t.id} aria-controls={detalleId}
          onClick={event => { triggerRef.current = event.currentTarget; setSeleccion(value => value === t.id ? null : t.id); }}
          className={`cursor-pointer min-h-36 rounded-xl border px-2 py-5 sm:px-5 text-center backdrop-blur-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-400 ${t.tone} ${seleccion === t.id ? "ring-2 ring-white/70" : ""}`}>
          <span className="block text-sm sm:text-base font-semibold">{t.label}</span>
          <span className="mt-1 block text-4xl sm:text-5xl font-semibold tabular-nums">{t.visitas.length}</span>
          <span className="mt-2 block text-xs">{seleccion === t.id ? "Cerrar ▴" : "Ver visitas ▾"}</span>
        </button>)}
      </div>
      <p className="text-xs text-gray-400">Actualizado: {horaPresencia(new Date(datos.fecha).toISOString())}. Hora de Ciudad de México.</p>
      {resumen.ultimo && <p className="text-sm mt-3">Último movimiento: {resumen.ultimo.tipo} de <strong>{resumen.ultimo.visita.nombre_visitante}</strong> · {horaPresencia(resumen.ultimo.fecha)}</p>}
      <div id={detalleId} hidden={!actual} className="mt-4" role="region" aria-label={actual?.label}>
        <h3 className="font-semibold">{actual?.label}</h3>
        <p role="status" className="text-xs text-gray-400 mt-1">{actual?.visitas.length ?? 0} visitas en esta selección.</p>
        {actual?.visitas.length === 0 ? <p className="mt-3 text-gray-300">No hay visitas para este estado.</p> : <ul className="mt-3 space-y-3">
          {actual?.visitas.map(v => <li key={v.visita_id} className="border-t border-gray-700 pt-3">
            <p className="font-medium">{v.nombre_visitante}{!residente && <span className="text-sm text-gray-400"> · {v.casa_unidad}</span>}</p>
            <p className="text-sm text-gray-300">Entrada: {v.entrada_registrada_en ? horaPresencia(v.entrada_registrada_en) : "Sin entrada registrada"}</p>
            <p className="text-sm text-gray-300">Salida: {v.salida_registrada_en ? horaPresencia(v.salida_registrada_en) : "Sin salida registrada"}</p>
            {seleccion === "dentro" && datos.fecha - instante(v.entrada_registrada_en)! >= 86400000 && <p className="text-xs text-amber-300 mt-1">Más de 24 horas sin salida registrada. Conviene revisar el registro con vigilancia.</p>}
          </li>)}
        </ul>}
      </div>
      {resumen.revisar.length > 0 && <details className="mt-4 rounded-lg border border-amber-700 p-3 text-amber-200"><summary>{resumen.revisar.length} registros por revisar · excluidos de los indicadores</summary><ul className="mt-2 text-sm">{resumen.revisar.map(v => <li key={v.visita_id}>{v.nombre_visitante}: estado y fechas no coinciden.</li>)}</ul></details>}
    </>}
  </section>;
}
