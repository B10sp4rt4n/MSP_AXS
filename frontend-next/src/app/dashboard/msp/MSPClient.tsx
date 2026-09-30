"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import UsuariosCondominio from "@/components/UsuariosCondominio";

type CasaResidente = { usuario_id: string; nombre: string; email: string; rol: string } | null;
type Casa = { casa_unidad: string; residente: CasaResidente };
type Condominio = {
  condominio_id: string;
  nombre: string;
  msp_id: string;
  total_usuarios: number;
  casas: Casa[];
};
type MSP = { msp_id: string; nombre: string; total_condominios: number };

type Tab = "condominios" | "usuarios";

export default function MSPClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [tab, setTab] = useState<Tab>("condominios");
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [msps, setMsps] = useState<MSP[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const cargar = () => {
    setLoading(true);
    setError("");
    getToken().then(async (token) => {
      if (!token) { setError("Sin sesión — recarga la página"); setLoading(false); return; }
      const [condosResult, mspsResult] = await Promise.allSettled([
        api.get<Condominio[]>("/condominios/", token),
        api.get<MSP[]>("/msps/", token),
      ]);
      if (condosResult.status === "fulfilled") {
        setCondominios(condosResult.value);
      } else {
        const msg = condosResult.reason instanceof Error ? condosResult.reason.message : String(condosResult.reason);
        setError(`Condominios: ${msg}`);
      }
      if (mspsResult.status === "fulfilled") {
        setMsps(mspsResult.value);
      }
      // MSPs fallback silencioso si 403 (no MSP_ADMIN) — los condominios aún se muestran
      setLoading(false);
    }).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Error de red");
      setLoading(false);
    });
  };

  useEffect(() => { cargar(); }, [getToken]);

  // Todos los usuarios aplanados de todos los condominios
  const todosUsuarios = condominios.flatMap(c =>
    c.casas
      .filter(ca => ca.residente)
      .map(ca => ({
        ...ca.residente!,
        casa_unidad: ca.casa_unidad,
        condominio: c.nombre,
        condominio_id: c.condominio_id,
      }))
  );

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="text-gray-400 hover:text-white text-sm">
            ← Inicio
          </button>
          <div>
            <h1 className="text-lg font-bold">Dashboard MSP</h1>
            <p className="text-xs text-gray-500">{msps[0]?.nombre ?? ""}</p>
          </div>
        </div>
        <div className="flex gap-3 text-center">
          <Stat label="Condominios" value={condominios.length} />
          <Stat label="Residentes" value={todosUsuarios.length} />
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-4 flex gap-1">
        {(["condominios", "usuarios"] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-3 text-sm font-medium capitalize transition-colors ${
              tab === t ? "border-b-2 border-blue-500 text-white" : "text-gray-400 hover:text-white"
            }`}>
            {t === "condominios" ? "Condominios" : "Usuarios"}
          </button>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm p-4">{error}</p>}

      <main className="p-4 max-w-4xl mx-auto">
        {loading ? (
          <p className="text-gray-500 text-sm pt-8 text-center">Cargando...</p>
        ) : tab === "condominios" ? (
          <TabCondominios
            condominios={condominios}
            msps={msps}
            getToken={getToken}
            onCreado={cargar}
            router={router}
          />
        ) : (
          <div>
            {condominios.length === 0 ? <p className="text-gray-400">Crea un condominio para asignar personal.</p> :
              condominios.map(c => <section key={c.condominio_id} className="mb-8">
                <h2 className="text-lg font-semibold mb-3">{c.nombre}</h2>
                <UsuariosCondominio condominioId={c.condominio_id} getToken={getToken} />
              </section>)}
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-800 rounded-lg px-4 py-2 min-w-[80px]">
      <p className="text-xl font-bold text-white">{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  );
}

// ─── Tab Condominios ──────────────────────────────────────────────────────────

function TabCondominios({
  condominios, msps, getToken, onCreado, router
}: {
  condominios: Condominio[];
  msps: { msp_id: string; nombre: string }[];
  getToken: () => Promise<string | null>;
  onCreado: () => void;
  router: ReturnType<typeof useRouter>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: "", msp_id: msps[0]?.msp_id ?? "" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (msps[0] && !form.msp_id) setForm(f => ({ ...f, msp_id: msps[0].msp_id }));
  }, [msps]);

  const crear = async () => {
    if (!form.nombre.trim()) { setFormError("El nombre es requerido"); return; }
    if (!form.msp_id) { setFormError("Selecciona un MSP"); return; }
    setSaving(true);
    setFormError("");
    try {
      const token = await getToken();
      await api.post("/condominios/", { nombre: form.nombre.trim(), msp_id: form.msp_id }, token!);
      setShowForm(false);
      setForm(f => ({ ...f, nombre: "" }));
      onCreado();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Error al crear");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">{condominios.length} condominio(s)</p>
        <button onClick={() => { setShowForm(!showForm); setFormError(""); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg">
          {showForm ? "Cancelar" : "+ Nuevo Condominio"}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-200">Nuevo condominio</h3>
          <input
            placeholder="Nombre del condominio"
            value={form.nombre}
            onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
          />
          {msps.length > 1 && (
            <select value={form.msp_id} onChange={e => setForm(f => ({ ...f, msp_id: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
              {msps.map(m => <option key={m.msp_id} value={m.msp_id}>{m.nombre}</option>)}
            </select>
          )}
          {formError && <p className="text-red-400 text-xs">{formError}</p>}
          <button onClick={crear} disabled={saving}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm">
            {saving ? "Creando..." : "Crear Condominio"}
          </button>
        </div>
      )}

      {condominios.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          <p className="text-4xl mb-3">🏘️</p>
          <p>Sin condominios registrados</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {condominios.map(c => (
            <div key={c.condominio_id} className="bg-gray-900 border border-gray-700 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-white">{c.nombre}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{c.condominio_id}</p>
                </div>
              </div>
              <div className="flex gap-4 mb-4">
                <div className="text-center">
                  <p className="text-lg font-bold text-white">{c.total_usuarios}</p>
                  <p className="text-xs text-gray-400">usuarios</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-white">{c.casas.length}</p>
                  <p className="text-xs text-gray-400">casas</p>
                </div>
              </div>
              <button
                onClick={() => {
                  localStorage.setItem("axs_condominio_id", c.condominio_id);
                  router.push("/dashboard/admin");
                }}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white text-sm font-semibold py-2 rounded-lg transition-colors"
              >
                Gestionar →
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

