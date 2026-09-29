"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Visita, Condominio, CasasResponse, CasaItem, ResidenteCasa } from "@/lib/types";

const CONDOMINIO_KEY = "axs_condominio_id";
type Tab = "visitas" | "casas" | "usuarios";

export default function AdminClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [tab, setTab] = useState<Tab>("visitas");
  const [condominioId, setCondominioId] = useState("");
  const [condominios, setCondominios] = useState<Condominio[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(CONDOMINIO_KEY);
    getToken().then(token => api.get<Condominio[]>("/condominios/", token!))
      .then(data => {
        setCondominios(data);
        setCondominioId(stored || data[0]?.condominio_id || "");
      })
      .catch(() => setError("No se pudieron cargar los condominios"));
  }, [getToken]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="text-gray-400 hover:text-white text-sm">
            ← Inicio
          </button>
          <h1 className="text-lg font-bold">Panel Admin</h1>
        </div>
        <select
          value={condominioId}
          onChange={e => { setCondominioId(e.target.value); localStorage.setItem(CONDOMINIO_KEY, e.target.value); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm"
        >
          {condominios.map(c => (
            <option key={c.condominio_id} value={c.condominio_id}>{c.nombre}</option>
          ))}
        </select>
      </header>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-4 flex gap-1">
        {(["visitas", "casas", "usuarios"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-3 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? "border-b-2 border-blue-500 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {t === "visitas" ? "Visitas" : t === "casas" ? "Casas / Unidades" : "Usuarios"}
          </button>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm p-4">{error}</p>}

      <main className="p-4 max-w-3xl mx-auto">
        {condominioId && tab === "visitas" && <TabVisitas condominioId={condominioId} getToken={getToken} />}
        {condominioId && tab === "casas"   && <TabCasas   condominioId={condominioId} getToken={getToken} />}
        {condominioId && tab === "usuarios"&& <TabUsuarios condominioId={condominioId} getToken={getToken} />}
      </main>
    </div>
  );
}

// ─── Tab Visitas ────────────────────────────────────────────────────────────

function TabVisitas({ condominioId, getToken }: { condominioId: string; getToken: () => Promise<string | null> }) {
  const [visitas, setVisitas] = useState<Visita[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState("todos");

  const cargar = () => {
    setLoading(true);
    getToken().then(token =>
      api.get<Visita[]>(`/visitas/condominio/${condominioId}`, token!)
    ).then(setVisitas).catch(() => setVisitas([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [condominioId]);

  const estados = ["todos", "pendiente", "entrada_registrada", "salida_registrada"];
  const filtradas = filtroEstado === "todos" ? visitas : visitas.filter(v => v.estado === filtroEstado);

  const estadoColor: Record<string, string> = {
    pendiente:           "bg-yellow-500/20 text-yellow-300",
    entrada_registrada:  "bg-green-500/20 text-green-300",
    salida_registrada:   "bg-gray-500/20 text-gray-400",
    cancelada:           "bg-red-500/20 text-red-400",
  };

  const hora = (dt: string | null) =>
    dt ? new Date(dt).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <div>
      {/* Filtros */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2 flex-wrap">
          {estados.map(e => (
            <button
              key={e}
              onClick={() => setFiltroEstado(e)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                filtroEstado === e
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {e === "todos" ? "Todos" : e === "entrada_registrada" ? "Con entrada" : e === "salida_registrada" ? "Con salida" : "Pendiente"}
            </button>
          ))}
        </div>
        <button onClick={cargar} className="text-xs text-blue-400 hover:text-blue-300">Actualizar</button>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Cargando...</p>
      ) : filtradas.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-4xl mb-3">📋</p>
          <p>Sin visitas {filtroEstado !== "todos" ? `con estado "${filtroEstado}"` : "registradas"}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtradas.map(v => (
            <div key={v.visita_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-white">{v.nombre_visitante}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Casa {v.casa_unidad} · {v.tipo_visita}
                  </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${estadoColor[v.estado] ?? "bg-gray-700 text-gray-300"}`}>
                  {v.estado.replace("_", " ")}
                </span>
              </div>
              <div className="mt-3 flex gap-4 text-xs text-gray-500">
                <span>Entrada: {hora(v.entrada_registrada_en)}</span>
                <span>Salida: {hora(v.salida_registrada_en)}</span>
                <span className="ml-auto">{v.created_at ? new Date(v.created_at).toLocaleDateString("es-MX") : "Sin fecha"}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Tab Casas ───────────────────────────────────────────────────────────────

function TabCasas({ condominioId, getToken }: { condominioId: string; getToken: () => Promise<string | null> }) {
  const [casasData, setCasasData] = useState<CasasResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ numero: "", tipo: "casa" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  // Asignar residente por casa
  const [asignando, setAsignando] = useState<string | null>(null); // casa_id
  const [resForm, setResForm] = useState({ nombre: "", email: "" });
  const [resSaving, setResSaving] = useState(false);
  const [resError, setResError] = useState("");

  const cargar = () => {
    setLoading(true);
    getToken().then(token =>
      api.get<CasasResponse>(`/condominios/${condominioId}/casas`, token!)
    ).then(setCasasData).catch(() => setCasasData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [condominioId]);

  const crearCasa = async () => {
    if (!form.numero.trim()) { setFormError("El número es requerido"); return; }
    setSaving(true); setFormError("");
    try {
      const token = await getToken();
      await api.post(`/condominios/${condominioId}/casas`, { numero: form.numero.trim(), tipo: form.tipo }, token!);
      setShowForm(false);
      setForm({ numero: "", tipo: "casa" });
      cargar();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Error al crear");
    } finally { setSaving(false); }
  };

  const asignarResidente = async (casaId: string) => {
    if (!resForm.email.trim()) { setResError("Email requerido"); return; }
    setResSaving(true); setResError("");
    try {
      const token = await getToken();
      await api.post(`/condominios/${condominioId}/casas/${casaId}/residente`,
        { nombre: resForm.nombre.trim() || "Residente", email: resForm.email.trim() }, token!);
      setAsignando(null);
      setResForm({ nombre: "", email: "" });
      cargar();
    } catch (e: unknown) {
      setResError(e instanceof Error ? e.message : "Error al asignar");
    } finally { setResSaving(false); }
  };

  const tipoLabel: Record<string, string> = { casa: "Casa", depto: "Depto", local: "Local" };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">{casasData ? `${casasData.total_casas} unidad(es)` : ""}</p>
        <button onClick={() => { setShowForm(!showForm); setFormError(""); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg">
          {showForm ? "Cancelar" : "+ Nueva Unidad"}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-200">Nueva unidad</h3>
          <input
            placeholder="Número (ej. A-12, 101, Local 3)"
            value={form.numero}
            onChange={e => setForm(f => ({ ...f, numero: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
          />
          <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
            <option value="casa">Casa</option>
            <option value="depto">Departamento</option>
            <option value="local">Local comercial</option>
          </select>
          {formError && <p className="text-red-400 text-xs">{formError}</p>}
          <button onClick={crearCasa} disabled={saving}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm">
            {saving ? "Creando..." : "Crear Unidad"}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Cargando...</p>
      ) : !casasData || casasData.total_casas === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-4xl mb-3">🏠</p>
          <p>Sin unidades registradas</p>
        </div>
      ) : (
        <div className="space-y-3">
          {casasData.casas.map((item: CasaItem) => (
            <div key={item.casa_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="font-semibold text-white">{item.numero}</p>
                  <p className="text-xs text-gray-500">{tipoLabel[item.tipo] ?? item.tipo}</p>
                </div>
                {!item.residente && asignando !== item.casa_id && (
                  <button
                    onClick={() => { setAsignando(item.casa_id); setResForm({ nombre: "", email: "" }); setResError(""); }}
                    className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg">
                    + Residente
                  </button>
                )}
              </div>

              {item.residente ? (
                <div className="flex items-center justify-between text-sm mt-1">
                  <span className="text-gray-300">{item.residente.nombre}</span>
                  <span className="text-xs text-gray-500">{item.residente.email}</span>
                </div>
              ) : asignando === item.casa_id ? (
                <div className="mt-2 space-y-2">
                  <input placeholder="Nombre del residente"
                    value={resForm.nombre}
                    onChange={e => setResForm(f => ({ ...f, nombre: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                  <input type="email" placeholder="Email *"
                    value={resForm.email}
                    onChange={e => setResForm(f => ({ ...f, email: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                  {resError && <p className="text-red-400 text-xs">{resError}</p>}
                  <div className="flex gap-2">
                    <button onClick={() => asignarResidente(item.casa_id)} disabled={resSaving}
                      className="flex-1 bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-xs font-semibold py-1.5 rounded-lg">
                      {resSaving ? "Guardando..." : "Asignar"}
                    </button>
                    <button onClick={() => setAsignando(null)}
                      className="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold py-1.5 rounded-lg">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-600 mt-1">Sin residente asignado</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Tab Usuarios ────────────────────────────────────────────────────────────

function TabUsuarios({ condominioId, getToken }: { condominioId: string; getToken: () => Promise<string | null> }) {
  const [casasData, setCasasData] = useState<CasasResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getToken().then(token =>
      api.get<CasasResponse>(`/condominios/${condominioId}/casas`, token!)
    ).then(setCasasData).catch(() => setCasasData(null))
      .finally(() => setLoading(false));
  }, [condominioId]);

  const usuarios = casasData?.casas
    .filter(c => c.residente)
    .map(c => ({ ...c.residente!, numero: c.numero })) ?? [];

  const rolColor: Record<string, string> = {
    RESIDENTE:         "bg-blue-500/20 text-blue-300",
    GUARDIA:           "bg-orange-500/20 text-orange-300",
    ADMIN_CONDOMINIO:  "bg-purple-500/20 text-purple-300",
    MSP_ADMIN:         "bg-red-500/20 text-red-300",
  };

  return (
    <div>
      <p className="text-sm text-gray-400 mb-4">{usuarios.length} residente(s) asignado(s)</p>
      {loading ? (
        <p className="text-gray-500 text-sm">Cargando...</p>
      ) : usuarios.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-4xl mb-3">👥</p>
          <p>Sin residentes asignados</p>
        </div>
      ) : (
        <div className="space-y-2">
          {usuarios.map(u => (
            <div key={u.usuario_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-white text-sm">{u.nombre}</p>
                <p className="text-xs text-gray-400 mt-0.5">{u.email} · Unidad {u.numero}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${rolColor[u.rol] ?? "bg-gray-700 text-gray-300"}`}>
                {u.rol}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
