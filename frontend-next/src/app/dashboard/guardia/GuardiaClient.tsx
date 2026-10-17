"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Condominio } from "@/lib/types";
import type { Operacion } from "@/lib/guardia-flow";
import GuardiaOperacion from "@/components/GuardiaOperacion";

export default function GuardiaClient({ initialMode = null }: { initialMode?: Operacion | null }) {
  const { getToken } = useAuth();
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [condominioId, setCondominioId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [blocked, setBlocked] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    async function cargar() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Tu sesión terminó. Vuelve a iniciar sesión.");
        const data = await api.get<Condominio[]>("/condominios/", token, AbortSignal.timeout(20000));
        let stored = "";
        try { stored = localStorage.getItem("axs_condominio_id") || ""; } catch { /* Storage may be unavailable. */ }
        if (active) { setCondominios(data); setCondominioId(data.find(c => c.condominio_id === stored)?.condominio_id || data[0]?.condominio_id || ""); }
      } catch { if (active) setError("No pudimos comprobar tus condominios. Revisa tu conexión y vuelve a intentar."); }
      finally { if (active) setLoading(false); }
    }
    void cargar();
    return () => { active = false; };
  }, [getToken, revision]);
  useEffect(() => { if (condominioId) { try { localStorage.setItem("axs_condominio_id", condominioId); } catch { /* Keep operating without persistence. */ } } }, [condominioId]);
  return <div className="min-h-screen bg-gray-950 text-white">
    <header className="flex items-center justify-between border-b border-gray-800 px-4 py-4"><h1 className="text-xl font-bold">AXS · Caseta</h1>{!blocked && <a href="/dashboard" className="rounded-lg px-4 py-3 text-gray-300">Inicio</a>}</header>
    <main className="mx-auto max-w-2xl space-y-6 p-4">
      {loading ? <p role="status">Comprobando acceso a caseta…</p> : error ? <div role="alert"><p>{error}</p><button className="min-h-12 rounded-xl border px-4" onClick={() => setRevision(v => v + 1)}>Reintentar</button></div> : !condominios.length ? <p>Sin condominio asignado. Solicita a administración que revise tus permisos.</p> : <>
        <div><label htmlFor="guardia-condominio" className="mb-2 block text-sm text-gray-300">Estás operando en</label>
          <select id="guardia-condominio" disabled={blocked || condominios.length === 1} value={condominioId} onChange={e => setCondominioId(e.target.value)} className="min-h-12 w-full rounded-xl border border-gray-600 bg-gray-900 px-3 text-lg">
            {condominios.map(c => <option key={c.condominio_id} value={c.condominio_id}>{c.nombre}</option>)}
          </select>
        </div>
        <GuardiaOperacion key={condominioId} condominioId={condominioId} initialMode={initialMode} onBlocked={setBlocked} />
      </>}
    </main>
  </div>;
}
