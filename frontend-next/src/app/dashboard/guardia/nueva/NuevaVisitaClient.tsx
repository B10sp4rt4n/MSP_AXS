"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Condominio } from "@/lib/types";

const CONDOMINIO_KEY = "axs_condominio_id";

export default function NuevaVisitaClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [condominioId, setCondominioId] = useState("");
  const [form, setForm] = useState({
    nombre_visitante: "",
    destino_id: "",
    destino_motivo: "",
    tipo_visita: "eventual",
    placa: "",
  });
  const [destinos, setDestinos] = useState<{ destino_id: string; nombre: string; tipo: string }[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(CONDOMINIO_KEY) || "";
    getToken().then(token => api.get<Condominio[]>("/condominios/", token!)).then((data) => {
      setCondominios(data);
      setCondominioId(data.find(c => c.condominio_id === stored)?.condominio_id || data[0]?.condominio_id || "");
    }).catch((e: unknown) => setError(e instanceof Error ? e.message : "Error al cargar condominios"));
  }, [getToken]);

  useEffect(() => {
    let active = true;
    setDestinos([]); setCatalogError("");
    setForm(f => ({ ...f, destino_id: "", destino_motivo: "" }));
    if (!condominioId) return;
    setCatalogLoading(true);
    getToken().then(token => {
      if (!token) throw new Error("Sin sesión");
      return api.get<{ destino_id: string; nombre: string; tipo: string }[]>(
        `/condominios/${encodeURIComponent(condominioId)}/destinos`, token);
    }).then(data => { if (active) setDestinos(data); })
      .catch((e: unknown) => { if (active) setCatalogError(e instanceof Error ? e.message : "Error al cargar destinos"); })
      .finally(() => { if (active) setCatalogLoading(false); });
    return () => { active = false; };
  }, [condominioId, getToken]);

  const set = (field: string, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!condominioId) return;
    if (!form.destino_id || catalogLoading || catalogError) { setError("Selecciona un destino del catálogo"); return; }
    setLoading(true);
    setError("");
    try {
      const token = await getToken();
      const vigencia = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      await api.post(`/visitas/entrada/${condominioId}`, { ...form, condominio_id: condominioId, vigencia }, token!);
      router.push("/dashboard/guardia");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : JSON.stringify(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center gap-3">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-white">←</button>
        <h1 className="text-lg font-bold">Registrar Visita</h1>
      </header>

      <main className="p-4 max-w-md mx-auto">
        <form onSubmit={submit} className="space-y-4 mt-2">

          {/* Condominio */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Condominio</label>
            <select
              value={condominioId}
              onChange={(e) => setCondominioId(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm"
            >
              {condominios.map((c) => (
                <option key={c.condominio_id} value={c.condominio_id}>{c.nombre}</option>
              ))}
            </select>
          </div>

          {/* Nombre visitante */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Nombre del visitante *</label>
            <input
              required
              type="text"
              placeholder="Ej. Juan Pérez"
              value={form.nombre_visitante}
              onChange={(e) => set("nombre_visitante", e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block" htmlFor="destino">Destino *</label>
            <select id="destino" required disabled={catalogLoading || loading} value={form.destino_id}
              onChange={e => set("destino_id", e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm">
              <option value="">{catalogLoading ? "Cargando destinos..." : "Selecciona un destino"}</option>
              <optgroup label="Viviendas">
                {destinos.filter(d => ["casa", "depto", "local"].includes(d.tipo)).map(d =>
                  <option key={d.destino_id} value={d.destino_id}>{d.nombre}</option>)}
              </optgroup>
              <optgroup label="Destinos comunes">
                {destinos.filter(d => ["administracion", "mantenimiento", "area_comun"].includes(d.tipo)).map(d =>
                  <option key={d.destino_id} value={d.destino_id}>{d.nombre}</option>)}
              </optgroup>
              <option value="OTRO">Otro destino (excepción)</option>
            </select>
            {catalogError && <p role="alert" className="text-red-400 text-sm mt-2">{catalogError}</p>}
          </div>
          {form.destino_id === "OTRO" && <div>
            <label htmlFor="motivo" className="text-xs text-gray-400 mb-1 block">Motivo de la excepción *</label>
            <textarea id="motivo" required minLength={5} maxLength={500} value={form.destino_motivo}
              onChange={e => set("destino_motivo", e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm" />
          </div>}

          {/* Tipo de visita */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Tipo de visita</label>
            <div className="grid grid-cols-3 gap-2">
              {["eventual", "frecuente", "proveedor"].map((tipo) => (
                <button
                  key={tipo}
                  type="button"
                  onClick={() => set("tipo_visita", tipo)}
                  className={`py-2 rounded-lg text-sm font-medium capitalize border transition-all ${
                    form.tipo_visita === tipo
                      ? "bg-blue-600 border-blue-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500"
                  }`}
                >
                  {tipo}
                </button>
              ))}
            </div>
          </div>

          {/* Placa (opcional) */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Placa vehicular (opcional)</label>
            <input
              type="text"
              placeholder="Ej. ABC-123"
              value={form.placa}
              onChange={(e) => set("placa", e.target.value.toUpperCase())}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading || catalogLoading || !!catalogError || !form.destino_id}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-xl text-sm mt-2"
          >
            {loading ? "Registrando..." : "Registrar Entrada"}
          </button>
        </form>
      </main>
    </div>
  );
}
