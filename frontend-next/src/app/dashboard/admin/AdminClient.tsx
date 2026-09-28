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
                <span className="ml-auto">{new Date(v.created_at).toLocaleDateString("es-MX")}</span>
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
  const [form, setForm] = useState({ casa_unidad: "", residente_nombre: "", residente_email: "" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [formOk, setFormOk] = useState("");

  const cargar = () => {
    setLoading(true);
    getToken().then(token =>
      api.get<CasasResponse>(`/condominios/${condominioId}/casas`, token!)
    ).then(setCasasData).catch(() => setCasasData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [condominioId]);

  const crear = async () => {
    if (!form.casa_unidad.trim()) { setFormError("El número de casa es requerido"); return; }
    if (!form.residente_email.trim()) { setFormError("El email del residente es requerido"); return; }
    setSaving(true);
    setFormError("");
    setFormOk("");
    try {
      const token = await getToken();
      await api.post(`/condominios/${condominioId}/casas`, {
        casa_unidad: form.casa_unidad.trim(),
        residente_nombre: form.residente_nombre.trim() || undefined,
        residente_email: form.residente_email.trim(),
      }, token!);
      setFormOk("Casa creada correctamente");
      setForm({ casa_unidad: "", residente_nombre: "", residente_email: "" });
      setShowForm(false);
      cargar();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al crear casa";
      setFormError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">
          {casasData ? `${casasData.total_casas} casa(s) registrada(s)` : ""}
        </p>
        <button
          onClick={() => { setShowForm(!showForm); setFormError(""); setFormOk(""); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          {showForm ? "Cancelar" : "+ Nueva Casa"}
        </button>
      </div>

      {formOk && <p className="text-green-400 text-sm mb-3">{formOk}</p>}

      {showForm && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-200">Nueva casa / unidad</h3>
          <input
            placeholder="Número o ID de casa (ej. A-12)"
            value={form.casa_unidad}
            onChange={e => setForm(f => ({ ...f, casa_unidad: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
          />
          <input
            placeholder="Nombre del residente (opcional)"
            value={form.residente_nombre}
            onChange={e => setForm(f => ({ ...f, residente_nombre: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
          />
          <input
            type="email"
            placeholder="Email del residente *"
            value={form.residente_email}
            onChange={e => setForm(f => ({ ...f, residente_email: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
          />
          {formError && <p className="text-red-400 text-xs">{formError}</p>}
          <button
            onClick={crear}
            disabled={saving}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm"
          >
            {saving ? "Guardando..." : "Crear Casa"}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm">Cargando...</p>
      ) : !casasData || casasData.total_casas === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-4xl mb-3">🏠</p>
          <p>Sin casas registradas</p>
        </div>
      ) : (
        <div className="space-y-3">
          {casasData.casas.map((item: CasaItem) => (
            <div key={item.casa_unidad} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="font-semibold text-white">Casa {item.casa_unidad}</p>
                <span className="text-xs text-gray-500">{item.residentes.length} usuario(s)</span>
              </div>
              <div className="space-y-1">
                {item.residentes.map(r => (
                  <div key={r.usuario_id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">{r.nombre}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{r.email}</span>
                      <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">{r.rol}</span>
                    </div>
                  </div>
                ))}
              </div>
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

  // Aplanar todos los usuarios de todas las casas
  const usuarios: (ResidenteCasa & { casa_unidad: string })[] = [];
  if (casasData) {
    for (const item of casasData.casas) {
      for (const r of item.residentes) {
        usuarios.push({ ...r, casa_unidad: item.casa_unidad });
      }
    }
  }

  const rolColor: Record<string, string> = {
    RESIDENTE:         "bg-blue-500/20 text-blue-300",
    GUARDIA:           "bg-orange-500/20 text-orange-300",
    ADMIN_CONDOMINIO:  "bg-purple-500/20 text-purple-300",
    MSP_ADMIN:         "bg-red-500/20 text-red-300",
  };

  return (
    <div>
      <p className="text-sm text-gray-400 mb-4">{usuarios.length} usuario(s) en este condominio</p>

      {loading ? (
        <p className="text-gray-500 text-sm">Cargando...</p>
      ) : usuarios.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          <p className="text-4xl mb-3">👥</p>
          <p>Sin usuarios registrados</p>
        </div>
      ) : (
        <div className="space-y-2">
          {usuarios.map(u => (
            <div key={u.usuario_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-white text-sm">{u.nombre}</p>
                <p className="text-xs text-gray-400 mt-0.5">{u.email} · Casa {u.casa_unidad}</p>
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
