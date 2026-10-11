"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Fila = { fila: number; vivienda: string; nombre: string; correo: string; estado: string; errores: string[] };
type Resultado = { filas: Fila[]; revision: string; nuevos: number; existentes: number; errores: number; confirmado: boolean; creados?: number };

function descargar(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a"); link.href = url; link.download = nombre; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function ImportarResidentes({ condominioId, getToken, onImported }: {
  condominioId: string; getToken: () => Promise<string | null>; onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [encoded, setEncoded] = useState("");
  const [result, setResult] = useState<Resultado | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const path = `/condominios/${encodeURIComponent(condominioId)}/residentes`;
  async function plantilla() {
    setBusy(true); setError("");
    try {
      const token = await getToken(); if (!token) throw new Error("Inicia sesión nuevamente");
      descargar(await api.download(`${path}/plantilla`, token), "AXS_residentes.xlsx");
    } catch (e) { setError(e instanceof Error ? e.message : "Error al descargar"); }
    finally { setBusy(false); }
  }
  async function procesar(confirm: boolean) {
    setBusy(true); setError("");
    try {
      const token = await getToken(); if (!token) throw new Error("Inicia sesión nuevamente");
      let archivo = encoded;
      if (!confirm) {
        setResult(null); setEncoded("");
        if (!file || !file.name.toLowerCase().endsWith(".xlsx")) throw new Error("Selecciona un archivo .xlsx");
        if (file.size > 2 * 1024 * 1024) throw new Error("El máximo es 2 MB");
        archivo = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(",")[1]);
          reader.onerror = () => reject(new Error("No se pudo leer el archivo"));
          reader.readAsDataURL(file);
        });
        setEncoded(archivo);
      }
      const data = await api.post<Resultado>(`${path}/importar`, {
        archivo, ...(confirm && result ? { revision: result.revision } : {}),
      }, token);
      setResult(data);
      if (data.confirmado) onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo procesar");
      if (confirm) setResult(null);
    } finally { setBusy(false); }
  }
  function reporte() {
    if (!result) return;
    const safe = (value: string) => `"${(/^[=+@\-\t\r]/.test(value) ? "'" : "") + value.replaceAll('"', '""')}"`;
    const rows = [["fila", "vivienda", "nombre", "correo", "estado", "observaciones"],
      ...result.filas.map(r => [String(r.fila), r.vivienda, r.nombre, r.correo, r.estado, r.errores.join("; ")])];
    descargar(new Blob(["\uFEFF" + rows.map(r => r.map(safe).join(",")).join("\r\n")],
      { type: "text/csv;charset=utf-8" }), "AXS_resultado_importacion.csv");
  }
  return <section className="border border-gray-700 rounded-xl p-4 mb-5 space-y-3" aria-label="Importar residentes">
    <h3 className="font-semibold">Alta por Excel</h3>
    <p className="text-sm text-gray-400">Hasta 500 viviendas con su residente. Se cargan en el condominio seleccionado. Las cuentas se vinculan al registrarse; no se envían invitaciones.</p>
    <button disabled={busy} onClick={plantilla} className="text-blue-300 disabled:opacity-50">Descargar plantilla</button>
    <label className="block text-sm">Archivo de residentes
      <input type="file" accept=".xlsx" disabled={busy} className="block mt-2 max-w-full" onChange={e => {
        setFile(e.target.files?.[0] ?? null); setResult(null); setEncoded(""); setError("");
      }} />
    </label>
    <button disabled={busy || !file} onClick={() => procesar(false)} className="bg-blue-600 rounded-lg px-4 py-2 disabled:opacity-50">
      {busy ? "Procesando…" : "Validar archivo"}
    </button>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {result && <div className="space-y-3">
      <p role="status">{result.confirmado ? `${result.creados} residentes creados.` : `${result.nuevos} nuevos.`} {result.existentes} existentes. {result.errores} filas con errores.</p>
      {result.errores > 0 && <p>Corrige el Excel y vuelve a validarlo. Todavía no se ha guardado ninguna fila.</p>}
      <div className="overflow-auto max-h-80"><table className="w-full text-sm text-left">
        <thead><tr>{["Fila", "Vivienda", "Nombre", "Correo", "Estado", "Observaciones"].map(h => <th key={h} className="p-2">{h}</th>)}</tr></thead>
        <tbody>{result.filas.map(r => <tr key={r.fila} className="border-t border-gray-700">
          <td className="p-2">{r.fila}</td><td className="p-2">{r.vivienda}</td><td className="p-2">{r.nombre}</td><td className="p-2">{r.correo}</td><td className="p-2">{r.estado}</td><td className="p-2">{r.errores.join("; ")}</td>
        </tr>)}</tbody>
      </table></div>
      <button onClick={reporte} className="text-blue-300 mr-4">Descargar resultado CSV</button>
      {!result.confirmado && result.errores === 0 && result.nuevos > 0 && <button disabled={busy} onClick={() => procesar(true)} className="bg-green-700 rounded-lg px-4 py-2 disabled:opacity-50">Confirmar {result.nuevos} altas</button>}
    </div>}
  </section>;
}
