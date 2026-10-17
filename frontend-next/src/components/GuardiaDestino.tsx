"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { CasaItem, CasasResponse } from "@/lib/types";
import { buscarDestinos, nombreDestino } from "@/lib/guardia-destino";

export default function GuardiaDestino({ condominioId, salida, onSelect }: { condominioId: string; salida: boolean; onSelect: (casa: CasaItem) => void }) {
  const { getToken } = useAuth();
  const [casas, setCasas] = useState<CasaItem[]>([]);
  const [consulta, setConsulta] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setCasas([]);
    async function cargar() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Sin sesión");
        const result = await api.get<CasasResponse>(`/condominios/${encodeURIComponent(condominioId)}/casas`, token, AbortSignal.timeout(20000));
        if (active) setCasas(result.casas);
      } catch { if (active) setError("No pudimos consultar el directorio. Revisa la conexión e intenta de nuevo."); }
      finally { if (active) setLoading(false); }
    }
    void cargar();
    return () => { active = false; };
  }, [condominioId, getToken, revision]);
  const resultados = buscarDestinos(casas, consulta);
  return <section className="space-y-4">
    <h2 className="text-2xl font-bold">{salida ? "¿De qué casa o lugar viene?" : "¿A quién visita o a qué casa va?"}</h2>
    <label htmlFor="destino-caseta" className="block text-gray-300">Nombre del residente, casa o lugar</label>
    <input id="destino-caseta" type="search" autoComplete="off" autoFocus value={consulta} onChange={e => setConsulta(e.target.value)} placeholder="Ej. Laura Gómez, casa 24 o administración" className="min-h-14 w-full rounded-xl border border-purple-400 bg-gray-900 px-4 text-lg" />
    {loading ? <p role="status">Buscando en el directorio…</p> : error ? <div role="alert"><p className="text-amber-200">{error}</p><button className="mt-3 min-h-12 rounded-xl border px-4" onClick={() => setRevision(v => v + 1)}>Reintentar</button></div> : <>
      {!consulta.trim() && <p className="text-gray-400">Escribe a quién busca o el lugar que te indique.</p>}
      {consulta.trim() && !resultados.length && <p role="status" className="text-amber-200">No encontramos ese nombre o destino. Confirma con la persona a quién visita; si no aparece, consulta a administración.</p>}
      <div className="space-y-3">
        {resultados.slice(0, 8).map(casa => <button type="button" key={casa.casa_id} aria-label={`Elegir ${nombreDestino(casa)}: ${(casa.residentes ?? (casa.residente ? [casa.residente] : [])).map(r => r.nombre).filter(Boolean).join(", ")}`} onClick={() => onSelect(casa)} className="min-h-20 w-full rounded-xl border border-gray-600 bg-gray-900 p-4 text-left hover:border-purple-400 focus-visible:outline-2 focus-visible:outline-purple-400">
          <span className="block text-xl font-semibold text-purple-200">{nombreDestino(casa)}</span>
          <span className="mt-1 block text-gray-200">{(casa.residentes ?? (casa.residente ? [casa.residente] : [])).map(r => r.nombre).filter(Boolean).join(" · ") || casa.descripcion || "Destino del condominio"}</span>
          <span className="mt-2 block text-sm text-gray-400">Elegir este destino →</span>
        </button>)}
      </div>
      {resultados.length > 8 && <p>Escribe el apellido o la casa para encontrar el destino exacto.</p>}
    </>}
  </section>;
}
