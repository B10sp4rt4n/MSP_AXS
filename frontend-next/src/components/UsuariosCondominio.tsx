"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Usuario = {
  usuario_id: string; nombre: string; email: string; rol: string;
  casa_unidad: string | null; casa_id: string | null; registro_pendiente: boolean;
};

export default function UsuariosCondominio({ condominioId, getToken }: {
  condominioId: string; getToken: () => Promise<string | null>;
}) {
  const [editing, setEditing] = useState<Usuario | null>(null);
  const [editForm, setEditForm] = useState({ nombre: "", email: "", rol: "GUARDIA", casa_id: "" });
  const [casas, setCasas] = useState<{ casa_id: string; numero: string; tipo: string }[]>([]);
  const [editError, setEditError] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [unitsLoading, setUnitsLoading] = useState(false);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [formError, setFormError] = useState("");
  const [form, setForm] = useState({ nombre: "", email: "", rol: "GUARDIA" });
  const cargar = useCallback(() => setRevision(r => r + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setUsuarios([]);
    getToken().then(token => {
      if (!token) throw new Error("Sin sesión; vuelve a iniciar sesión");
      return api.get<Usuario[]>(`/condominios/${encodeURIComponent(condominioId)}/usuarios`, token);
    }).then(data => { if (active) setUsuarios(data); })
      .catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : "Error al cargar usuarios"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [condominioId, getToken, revision]);

  const crear = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true); setFormError(""); setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión; vuelve a iniciar sesión");
      const result = await api.post<Usuario>(`/condominios/${encodeURIComponent(condominioId)}/usuarios`,
        { ...form, nombre: form.nombre.trim(), email: form.email.trim() }, token);
      setMessage(result.registro_pendiente
        ? `Alta lista para ${result.email}. Debe registrarse con ese mismo correo para entrar con su rol asignado.`
        : `Cuenta ${result.email} asignada. Al volver al inicio verá su nuevo rol.`);
      setShowForm(false); setForm({ nombre: "", email: "", rol: "GUARDIA" }); cargar();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Error al dar de alta");
    } finally { setSaving(false); }
  };

  const abrirEdicion = async (user: Usuario) => {
    setEditing(user); setEditError(""); setShowForm(false);
    setEditForm({ nombre: user.nombre, email: user.email, rol: user.rol, casa_id: user.casa_id ?? "" });
    setUnitsLoading(true); setCasas([]);
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const data = await api.get<{ casas: { casa_id: string; numero: string }[] }>(
        `/condominios/${encodeURIComponent(condominioId)}/casas`, token);
      setCasas(data.casas.filter(c => ["casa", "depto", "local"].includes(c.tipo)));
    } catch (e: unknown) {
      setEditError(e instanceof Error ? e.message : "No se pudieron cargar las viviendas");
    } finally { setUnitsLoading(false); }
  };

  const guardarEdicion = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    setEditSaving(true); setEditError(""); setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      await api.patch(
        `/condominios/${encodeURIComponent(condominioId)}/usuarios/${encodeURIComponent(editing.usuario_id)}`,
        { nombre: editForm.nombre.trim(), email: editForm.email.trim(), rol: editForm.rol,
          casa_id: editForm.rol === "RESIDENTE" ? editForm.casa_id || null : null }, token);
      setEditing(null); setMessage("Cuenta actualizada."); cargar();
    } catch (e: unknown) {
      setEditError(e instanceof Error ? e.message : "Error al actualizar");
    } finally { setEditSaving(false); }
  };

  const labels: Record<string, string> = {
    GUARDIA: "Guardia", ADMIN_CONDOMINIO: "Administrador", RESIDENTE: "Residente", LECTURA: "Lectura",
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">{usuarios.length} usuario(s)</p>
        <button onClick={() => { setShowForm(v => !v); setEditing(null); setFormError(""); }} disabled={saving || editSaving}
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
          {showForm ? "Cancelar" : "+ Nuevo personal"}
        </button>
      </div>
      {message && <p role="status" className="text-green-300 text-sm mb-4">{message}</p>}
      {showForm && (
        <form onSubmit={crear} className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-4 space-y-3">
          <h3 className="font-semibold">Alta de personal</h3>
          <label className="block text-sm">Nombre
            <input required maxLength={200} value={form.nombre} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2" />
          </label>
          <label className="block text-sm">Correo
            <input required type="email" maxLength={254} value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2" />
          </label>
          <label className="block text-sm">Rol
            <select value={form.rol} onChange={e => setForm(f => ({ ...f, rol: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
              <option value="GUARDIA">Guardia</option>
              <option value="ADMIN_CONDOMINIO">Administrador del condominio</option>
            </select>
          </label>
          <p className="text-xs text-gray-400">Sólo el MSP puede dar de alta administradores. Los residentes se asignan desde Casas / Unidades.</p>
          {formError && <p role="alert" className="text-red-400 text-sm">{formError}</p>}
          <button disabled={saving} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm">
            {saving ? "Guardando..." : "Dar de alta"}
          </button>
        </form>
      )}
      {editing && (
        <form onSubmit={guardarEdicion} className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-4 space-y-3">
          <h3 className="font-semibold">Editar cuenta</h3>
          <label className="block text-sm">Nombre
            <input required maxLength={200} value={editForm.nombre}
              onChange={e => setEditForm(f => ({ ...f, nombre: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2" />
          </label>
          <label className="block text-sm">Correo
            <input required type="email" maxLength={254} readOnly={!editing.registro_pendiente} value={editForm.email}
              onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 read-only:text-gray-400" />
          </label>
          {!editing.registro_pendiente && <p className="text-xs text-gray-400">
            Para cambiar el correo de acceso, la persona debe abrir su avatar → Administrar cuenta y verificar el nuevo correo.
          </p>}
          <label className="block text-sm">Rol
            <select value={editForm.rol} onChange={e => setEditForm(f => ({ ...f, rol: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
              <option value="GUARDIA">Guardia</option>
              <option value="ADMIN_CONDOMINIO">Administrador del condominio</option>
              <option value="RESIDENTE">Residente</option>
            </select>
          </label>
          {editForm.rol === "RESIDENTE" && <label className="block text-sm">Vivienda
            <select disabled={unitsLoading} value={editForm.casa_id} onChange={e => setEditForm(f => ({ ...f, casa_id: e.target.value }))}
              className="w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
              <option value="">Selecciona una vivienda</option>
              {casas.map(c => <option key={c.casa_id} value={c.casa_id}>{c.numero}</option>)}
            </select>
          </label>}
          <p className="text-xs text-gray-400">Cambiar roles o editar administradores requiere una cuenta MSP.</p>
          {editError && <p role="alert" className="text-red-400 text-sm">{editError}</p>}
          <div className="flex gap-2">
            <button disabled={editSaving || unitsLoading} className="bg-blue-600 px-4 py-2 rounded-lg text-sm disabled:opacity-50">
              {editSaving ? "Guardando..." : "Guardar cambios"}
            </button>
            <button type="button" disabled={editSaving} onClick={() => setEditing(null)}
              className="bg-gray-700 px-4 py-2 rounded-lg text-sm">Cancelar</button>
          </div>
        </form>
      )}
      {error && <p role="alert" className="text-red-400 text-sm mb-3">{error}</p>}
      <button onClick={cargar} className="text-blue-400 text-xs mb-3">Actualizar</button>
      {loading ? <p className="text-gray-400 text-sm">Cargando...</p> : !error && usuarios.length === 0
        ? <p className="text-gray-500">Sin usuarios asignados</p>
        : <div className="space-y-2">{usuarios.map(u => (
          <div key={u.usuario_id} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
            <button disabled={editSaving || unitsLoading} onClick={() => abrirEdicion(u)}
              className="float-right text-blue-400 text-sm disabled:opacity-50">Editar</button>
            <p className="font-medium">{u.nombre} · {labels[u.rol] ?? u.rol}</p>
            <p className="text-sm text-gray-400">{u.email}{u.casa_unidad ? ` · Unidad ${u.casa_unidad}` : ""}</p>
            {u.registro_pendiente && <p className="text-xs text-yellow-300 mt-1">Registro de cuenta pendiente</p>}
          </div>
        ))}</div>}
    </div>
  );
}
