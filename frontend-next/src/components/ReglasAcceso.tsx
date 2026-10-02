"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

export interface Reglas {
  exigir_proposito: boolean;
  exigir_autorizacion: boolean;
  tipos_visita: string[];
}

const TIPOS = [
  ["eventual", "Eventual"], ["frecuente", "Frecuente"],
  ["visita_personal", "Personal"], ["proveedor", "Proveedor"], ["entrega", "Entrega"],
];

export function useReglasAcceso(condominioId?: string) {
  const { getToken } = useAuth();
  const [state, setState] = useState<{ reglas: Reglas | null; error: string; tenant: string }>({ reglas: null, error: "", tenant: "" });
  useEffect(() => {
    let active = true;
    if (condominioId === "") return;
    const cargar = async () => {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const id = condominioId ?? (await api.get<{ condominio_id: string }>("/auth/me", token)).condominio_id;
      if (!id) throw new Error("Sin condominio asignado");
      const reglas = await api.get<Reglas>(`/condominios/${encodeURIComponent(id)}/reglas-acceso`, token);
      if (active) setState({ reglas, error: "", tenant: condominioId ?? "perfil" });
    };
    cargar().catch((e: unknown) => {
      if (active) setState({ reglas: null, error: e instanceof Error ? e.message : "No se pudieron cargar las reglas", tenant: condominioId ?? "perfil" });
    });
    return () => { active = false; };
  }, [condominioId, getToken]);
  return state.tenant === (condominioId ?? "perfil") ? state : { reglas: null, error: "", tenant: "" };
}

export function CampoProposito({ value, onChange, required }: {
  value: string; onChange: (value: string) => void; required: boolean;
}) {
  return <div>
    <label htmlFor="proposito-visita" className="text-xs text-gray-400 mb-1 block">
      Propósito de la visita {required ? "(obligatorio)" : "(opcional)"}
    </label>
    <textarea id="proposito-visita" value={value} onChange={e => onChange(e.target.value)}
      required={required} maxLength={500} placeholder="Ej. Reparación del aire acondicionado"
      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm" />
  </div>;
}

export default function ConfigurarReglasAcceso({ condominioId }: { condominioId: string }) {
  const { getToken } = useAuth();
  const { reglas, error } = useReglasAcceso(condominioId);
  const [edit, setEdit] = useState<Reglas | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const actual = edit ?? reglas;

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!actual) return;
    setSaving(true); setMessage(""); setSaveError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const saved = await api.put<Reglas>(`/condominios/${encodeURIComponent(condominioId)}/reglas-acceso`, actual, token);
      setEdit(saved); setMessage("Reglas guardadas para este condominio.");
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "No se pudieron guardar las reglas");
    } finally { setSaving(false); }
  };

  if (error) return <p role="alert" className="text-red-400">{error}</p>;
  if (!actual) return <p className="text-gray-400">Cargando reglas...</p>;
  return <form onSubmit={guardar} className="space-y-5 bg-gray-900 border border-gray-700 rounded-xl p-5">
    <h2 className="font-semibold">Reglas de acceso</h2>
    <p className="text-sm text-gray-400">Elige las condiciones de este condominio. El vigilante no puede omitirlas. Sin autorización, se rechaza esa entrada y se continúa atendiendo.</p>
    <fieldset disabled={saving} className="space-y-4">
      <label className="flex gap-3 items-center"><input type="checkbox" checked={actual.exigir_proposito}
        onChange={e => { setEdit({ ...actual, exigir_proposito: e.target.checked }); setMessage(""); }} />Exigir propósito de la visita</label>
      <label className="flex gap-3 items-center"><input type="checkbox" checked={actual.exigir_autorizacion}
        onChange={e => { setEdit({ ...actual, exigir_autorizacion: e.target.checked }); setMessage(""); }} />Exigir autorización previa del residente o administración</label>
      <fieldset className="space-y-2">
        <legend className="text-sm text-gray-400 mb-2">Aplicar las reglas a estos tipos de visita</legend>
        {TIPOS.map(([value, label]) => <label key={value} className="flex gap-3 items-center text-sm">
          <input type="checkbox" checked={actual.tipos_visita.includes(value)} onChange={e => {
            setEdit({ ...actual, tipos_visita: e.target.checked ? [...actual.tipos_visita, value] : actual.tipos_visita.filter(t => t !== value) });
            setMessage("");
          }} />{label}
        </label>)}
      </fieldset>
    </fieldset>
    <p className="text-xs text-gray-400">Los cambios aplican a las siguientes entradas, incluidas visitas ya creadas. Las entradas registradas se conservan.</p>
    {(saveError || !actual.tipos_visita.length) && <p role="alert" className="text-red-400 text-sm">{saveError || "Selecciona al menos un tipo de visita."}</p>}
    {message && <p role="status" className="text-green-400 text-sm">{message}</p>}
    <button disabled={saving || !actual.tipos_visita.length} className="bg-blue-600 rounded-lg px-4 py-2 disabled:opacity-50">{saving ? "Guardando..." : "Guardar reglas"}</button>
  </form>;
}

export function AutorizarVisita({ visitaId, condominioId, proposito, onSaved }: {
  visitaId: string; condominioId: string; proposito?: string | null; onSaved: () => void;
}) {
  const { getToken } = useAuth();
  const [value, setValue] = useState(proposito ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const autorizar = async () => {
    setSaving(true); setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      await api.patch(`/visitas/${encodeURIComponent(visitaId)}/autorizar?condominio_id=${encodeURIComponent(condominioId)}`, { proposito: value }, token);
      onSaved();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "No se pudo autorizar"); }
    finally { setSaving(false); }
  };
  return <div className="mt-3 space-y-2">
    <label className="block text-xs text-gray-400">Propósito para autorizar
      <input value={value} onChange={e => setValue(e.target.value)} maxLength={500} disabled={saving}
        className="block w-full bg-gray-800 border border-gray-700 rounded p-2 mt-1" />
    </label>
    <button onClick={autorizar} disabled={saving} className="text-sm text-blue-400 disabled:opacity-50">{saving ? "Autorizando..." : "Autorizar visita"}</button>
    {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
  </div>;
}
