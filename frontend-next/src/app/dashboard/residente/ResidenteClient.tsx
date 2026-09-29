"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Visita, Condominio } from "@/lib/types";

const CONDOMINIO_KEY = "axs_condominio_id";

export default function ResidenteClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [condominioId, setCondominioId] = useState("");
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [visitas, setVisitas] = useState<Visita[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(CONDOMINIO_KEY) || "";
    getToken().then(token => api.get<Condominio[]>("/condominios/", token!))
      .then(data => {
        setCondominios(data);
        const id = stored || data[0]?.condominio_id || "";
        setCondominioId(id);
      })
      .catch(() => {});
  }, [getToken]);

  const loadVisitas = useCallback((id: string) => {
    if (!id) return;
    setLoading(true);
    getToken()
      .then(token => api.get<Visita[]>(`/visitas/mis-visitas/${id}`, token!))
      .then(setVisitas)
      .catch(() => setVisitas([]))
      .finally(() => setLoading(false));
  }, [getToken]);

  useEffect(() => {
    if (!condominioId) return;
    localStorage.setItem(CONDOMINIO_KEY, condominioId);
    loadVisitas(condominioId);
  }, [condominioId, loadVisitas]);

  const estadoColor: Record<string, string> = {
    pendiente:          "bg-yellow-500/20 text-yellow-300",
    activa:             "bg-green-500/20 text-green-300",
    entrada_registrada: "bg-blue-500/20 text-blue-300",
    salida_registrada:  "bg-gray-500/20 text-gray-400",
    completada:         "bg-gray-500/20 text-gray-400",
    cancelada:          "bg-red-500/20 text-red-400",
  };

  const hora = (dt: string | null) =>
    dt ? new Date(dt).toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" }) : "—";

  const cancelar = async (visitaId: string) => {
    try {
      const token = await getToken();
      await api.patch(`/visitas/${visitaId}/cancelar`, {}, token!);
      loadVisitas(condominioId);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Error al cancelar");
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="text-gray-400 hover:text-white">
            ← Inicio
          </button>
          <h1 className="text-lg font-bold">Portal Residente</h1>
        </div>
        <button
          onClick={() => router.push("/dashboard/residente/nueva")}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          + Preregistrar Visita
        </button>
      </header>

      <main className="p-4 max-w-2xl mx-auto">
        {condominios.length > 1 && (
          <div className="mb-4">
            <label className="text-xs text-gray-400 mb-1 block">Condominio</label>
            <select
              value={condominioId}
              onChange={(e) => setCondominioId(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
            >
              {condominios.map((c) => (
                <option key={c.condominio_id} value={c.condominio_id}>{c.nombre}</option>
              ))}
            </select>
          </div>
        )}

        <h2 className="text-sm font-semibold text-gray-300 mb-3">Mis visitas</h2>

        {loading ? (
          <p className="text-gray-500 text-sm">Cargando...</p>
        ) : visitas.length === 0 ? (
          <div className="text-center py-12 text-gray-600">
            <p className="text-4xl mb-3">📭</p>
            <p>Sin visitas registradas</p>
            <button
              onClick={() => router.push("/dashboard/residente/nueva")}
              className="mt-4 text-blue-400 text-sm hover:underline"
            >
              Preregistrar una visita →
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {visitas.map((v) => (
              <div key={v.visita_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-white">{v.nombre_visitante}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{v.tipo_visita}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${estadoColor[v.estado] ?? "bg-gray-700 text-gray-300"}`}>
                    {v.estado}
                  </span>
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  <span>Agendada: {hora(v.created_at)}</span>
                </div>
                {v.estado === "pendiente" && (
                  <button
                    onClick={() => cancelar(v.visita_id)}
                    className="mt-3 w-full border border-red-700 text-red-400 hover:bg-red-900/30 text-xs font-semibold py-1.5 rounded-lg"
                  >
                    Cancelar visita
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
