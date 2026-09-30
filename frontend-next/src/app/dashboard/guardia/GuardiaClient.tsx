"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Visita, Condominio } from "@/lib/types";

const CONDOMINIO_KEY = "axs_condominio_id";

export default function GuardiaClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [condominioId, setCondominioId] = useState<string>("");
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [visitas, setVisitas] = useState<Visita[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Cargar condominios disponibles
  useEffect(() => {
    const stored = localStorage.getItem(CONDOMINIO_KEY);
    getToken().then(token => api.get<Condominio[]>("/condominios/", token!))
      .then((data) => {
        setCondominios(data);
        const id = data.find(c => c.condominio_id === stored)?.condominio_id || data[0]?.condominio_id || "";
        setCondominioId(id);
      })
      .catch(() => setError("No se pudieron cargar los condominios"));
  }, [getToken]);

  // Cargar visitas al seleccionar condominio
  useEffect(() => {
    if (!condominioId) return;
    localStorage.setItem(CONDOMINIO_KEY, condominioId);
    setLoading(true);
    getToken().then(token =>
      api.get<Visita[]>(`/visitas/condominio/${condominioId}`, token!)
    ).then((data) => setVisitas(data))
      .catch(() => setVisitas([]))
      .finally(() => setLoading(false));
  }, [condominioId, getToken]);

  const refresh = useCallback(() => {
    if (!condominioId) return;
    getToken().then(token =>
      api.get<Visita[]>(`/visitas/condominio/${condominioId}`, token!)
    ).then(setVisitas).catch(() => {});
  }, [condominioId, getToken]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="text-gray-400 hover:text-white">
            ← Inicio
          </button>
          <h1 className="text-lg font-bold">Portal Guardia</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push("/dashboard/guardia/validar")}
            className="bg-green-700 hover:bg-green-600 text-white text-sm font-semibold px-4 py-2 rounded-lg"
          >
            Validar QR
          </button>
          <button
            onClick={() => router.push("/dashboard/guardia/nueva")}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
          >
            + Registrar
          </button>
        </div>
      </header>

      <main className="p-4 max-w-2xl mx-auto">
        {/* Selector de condominio */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 mb-1 block">Condominio</label>
          <select
            value={condominioId}
            onChange={(e) => setCondominioId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
          >
            {condominios.map((c) => (
              <option key={c.condominio_id} value={c.condominio_id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        {/* Lista de visitas */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300">Visitas de hoy</h2>
          <button onClick={refresh} className="text-xs text-blue-400 hover:text-blue-300">
            Actualizar
          </button>
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm">Cargando...</p>
        ) : visitas.length === 0 ? (
          <div className="text-center py-12 text-gray-600">
            <p className="text-4xl mb-3">🚗</p>
            <p>Sin visitas registradas hoy</p>
          </div>
        ) : (
          <div className="space-y-3">
            {visitas.map((v) => (
              <VisitaCard key={v.visita_id} condominioId={condominioId} visita={v} onRefresh={refresh} getToken={getToken} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function VisitaCard({
  condominioId,
  visita,
  onRefresh,
  getToken,
}: {
  condominioId: string;
  visita: Visita;
  onRefresh: () => void;
  getToken: () => Promise<string | null>;
}) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const estadoColor: Record<string, string> = {
    pendiente:           "bg-yellow-500/20 text-yellow-300",
    activa:              "bg-green-500/20 text-green-300",
    entrada_registrada:  "bg-blue-500/20 text-blue-300",
    salida_registrada:   "bg-gray-500/20 text-gray-400",
    completada:          "bg-gray-500/20 text-gray-400",
    cancelada:           "bg-red-500/20 text-red-400",
  };

  const hora = (dt: string | null) =>
    dt ? new Date(dt).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" }) : "—";

  const canExit = ["pendiente", "entrada_registrada", "activa"].includes(visita.estado);

  const registrarSalida = async () => {
    setLoading(true);
    setErr("");
    try {
      const token = await getToken();
      await api.patch(`/visitas/${visita.visita_id}/salida?condominio_id=${encodeURIComponent(condominioId)}`, {}, token!);
      onRefresh();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Error al registrar salida");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-white">{visita.nombre_visitante}</p>
          <p className="text-xs text-gray-400 mt-0.5">Casa {visita.casa_unidad} · {visita.tipo_visita}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${estadoColor[visita.estado] ?? "bg-gray-700 text-gray-300"}`}>
          {visita.estado}
        </span>
      </div>
      <div className="mt-3 flex gap-4 text-xs text-gray-500">
        <span>Entrada: {hora(visita.entrada_registrada_en)}</span>
        <span>Salida: {hora(visita.salida_registrada_en)}</span>
      </div>
      {err && <p className="text-red-400 text-xs mt-2">{err}</p>}
      {canExit && (
        <button
          onClick={registrarSalida}
          disabled={loading}
          className="mt-3 w-full bg-orange-700 hover:bg-orange-600 disabled:opacity-50 text-white text-xs font-semibold py-2 rounded-lg"
        >
          {loading ? "Registrando..." : "Registrar Salida"}
        </button>
      )}
    </div>
  );
}
