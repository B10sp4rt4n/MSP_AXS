"use client";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { CasaItem, Visita } from "@/lib/types";
import { buscarVisitas, evaluarVisita, type Operacion } from "@/lib/guardia-flow";
import SolicitudesAcceso from "@/components/SolicitudesAcceso";
import GuardiaDestino from "@/components/GuardiaDestino";
import { visitaEnDestino, nombreDestino } from "@/lib/guardia-destino";
import type { Reglas } from "@/components/ReglasAcceso";
import GuardiaQrScanner from "./GuardiaQrScanner";
import IdentificacionVisita from "@/components/IdentificacionVisita";

import EvidenciaSalida, { VistaFotoSalida } from "./EvidenciaSalida";

const button = "min-h-12 rounded-xl border border-gray-600 px-4 py-3 font-semibold hover:bg-gray-800 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-purple-400";
type Ficha = { visita: Visita; reglas: Reglas | null; qr: string | null };

export default function GuardiaOperacion({ condominioId, initialMode = null, onBlocked }: { condominioId: string; initialMode?: Operacion | null; onBlocked: (value: boolean) => void }) {
  const { getToken } = useAuth();
  const [operacion, setOperacion] = useState<Operacion>(initialMode ?? "entrada");
  const [abierto, setAbierto] = useState(false);
  const panelId = useId();
  const [destino, setDestino] = useState<CasaItem | null>(null);
  const [consulta, setConsulta] = useState("");
  const [historial, setHistorial] = useState(false);
  const [rows, setRows] = useState<Visita[] | null>(null);
  const [ficha, setFicha] = useState<Ficha | null>(null);
  const [foto, setFoto] = useState<{ file: File; captura: string } | null>(null);
  const [fotoAbierta, setFotoAbierta] = useState(false);
  const [fotoError, setFotoError] = useState("");
  const [fotoGuardada, setFotoGuardada] = useState(false);
  const [camara, setCamara] = useState(false);
  const [manual, setManual] = useState(false);
  const [codigo, setCodigo] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [incierto, setIncierto] = useState(false);
  const [exito, setExito] = useState<{ nombre: string; fecha: string; op: Operacion } | null>(null);
  useEffect(() => { onBlocked(busy || incierto); }, [busy, incierto, onBlocked]);
  const lock = useRef(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const token = useCallback(async () => {
    const t = await getToken();
    if (!t) throw new Error("Tu sesión terminó. Vuelve a iniciar sesión.");
    return t;
  }, [getToken]);
  const detalle = useCallback(async (id: string) => api.get<Visita>(`/visitas/${encodeURIComponent(id)}?condominio_id=${encodeURIComponent(condominioId)}`, await token(), AbortSignal.timeout(20000)), [condominioId, token]);
  function reset(op?: Operacion) {
    setFoto(null); setFotoAbierta(false); setFotoError(""); setFotoGuardada(false);
    setAbierto(op !== undefined);
    setDestino(null); setOperacion(op ?? "entrada"); setConsulta(""); setHistorial(false); setRows(null); setFicha(null); setCamara(false); setManual(false);
    setCodigo(""); setError("");  setIncierto(false); setExito(null);
  }
  useEffect(() => {
    if (!exito || foto || busy) return;
    const timer = setTimeout(() => { reset(); }, 10000);
    return () => clearTimeout(timer);
  }, [exito, foto, busy]);
  async function buscar() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(""); setRows(null);
    try {
      const data = await api.get<Visita[]>(`/visitas/condominio/${encodeURIComponent(condominioId)}`, await token(), AbortSignal.timeout(20000));
      if (alive.current) setRows(data);
    } catch { if (alive.current) setError("No pudimos consultar las visitas. Comprueba la conexión y vuelve a buscar."); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const revisar = useCallback(async (id: string, qr: string | null = null) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(""); setFicha(null); setFoto(null); setFotoAbierta(false); setFotoError(""); setFotoGuardada(false);
    try {
      const v = await detalle(id);
      if (v.condominio_id !== condominioId) throw new Error("Esta visita no corresponde al condominio seleccionado.");
      if (!destino || !visitaEnDestino(v, destino)) throw new Error("Esta visita corresponde a otro destino. Confirma la casa con el visitante y vuelve a elegirla.");
      if (qr && qr !== v.qr_token) throw new Error("Este QR no corresponde al registro vigente. Busca sin QR para revisar la visita.");
      const reglas = await api.get<Reglas>(`/condominios/${encodeURIComponent(condominioId)}/reglas-acceso`, await token(), AbortSignal.timeout(20000)).catch(e => { if (operacion === "entrada") throw e; return null; });
      if (alive.current) setFicha({ visita: v, reglas, qr });
    } catch (e) { if (alive.current) setError(e instanceof Error && !/fetch|timeout|abort/i.test(e.message) ? e.message : "No pudimos revisar la visita. Comprueba tu conexión e intenta de nuevo."); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }, [condominioId, destino, detalle, operacion, token]);
  const leerQR = useCallback((value: string) => {
    setCamara(false);
    const parts = value.trim().split("|");
    if (parts.length !== 3 || parts[0] !== "AXS" || !parts[1] || !parts[2]) { setError("Este no es un QR de AXS. Escanea otro o busca sin QR."); return; }
    void revisar(parts[1], parts[2]);
  }, [revisar]);
  const resultado = ficha && operacion ? evaluarVisita(ficha.visita, operacion, ficha.reglas, ficha.qr) : null;
  const coincidencias = destino && rows ? buscarVisitas(rows.filter(v => visitaEnDestino(v, destino)), consulta, operacion, historial) : [];
  async function guardarFoto(id: string) {
    if (!foto) return;
    setFotoError("");
    try {
      const body = new FormData(); body.append("foto", foto.file); body.append("captura_id", foto.captura);
      await api.upload(`/evidencias-salida/${encodeURIComponent(id)}?condominio_id=${encodeURIComponent(condominioId)}`, body, await token(), AbortSignal.timeout(30000));
      if (alive.current) setFotoGuardada(true);
    } catch (e) { if (alive.current) setFotoError(`La salida quedó registrada. No se confirmó la foto. ${e instanceof Error ? e.message : "Puedes reintentar o continuar sin ella."}`); }
  }
  async function reintentarFoto() {
    if (!ficha || lock.current) return;
    lock.current = true; setBusy(true);
    try { await guardarFoto(ficha.visita.visita_id); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function cerrar(v: Visita, op: Operacion) {
    const fecha = op === "entrada" ? v.entrada_registrada_en : v.salida_registrada_en;
    if (!fecha) return false;
    if (alive.current) { setExito({ nombre: v.nombre_visitante, fecha, op }); setIncierto(false); setError(""); }
    if (op === "salida" && foto) await guardarFoto(v.visita_id);
    return true;
  }
  async function comprobar() {
    if (!ficha || !operacion || lock.current) return;
    lock.current = true; setBusy(true);
    try {
      const v = await detalle(ficha.visita.visita_id);
      if (!await cerrar(v, operacion) && alive.current) {
        setFicha({ ...ficha, visita: v }); setIncierto(false);
        setError("La consulta no muestra el movimiento. Revisa de nuevo los datos antes de confirmar; AXS impedirá duplicarlo si otra caseta ya lo registró.");
      }
    } catch { if (alive.current) setError("Seguimos sin poder confirmar el registro. No repitas la operación: comprueba otra vez o solicita apoyo a administración."); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function registrar() {
    if (!ficha || !operacion || incierto || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    let enviado = false;
    try {
      const v = await detalle(ficha.visita.visita_id);
      if (!destino || !visitaEnDestino(v, destino)) throw new Error("El destino cambió. Vuelve a identificar la visita.");
      const reglas = await api.get<Reglas>(`/condominios/${encodeURIComponent(condominioId)}/reglas-acceso`, await token(), AbortSignal.timeout(20000)).catch(e => { if (operacion === "entrada") throw e; return null; });
      const revision = evaluarVisita(v, operacion, reglas, ficha.qr);
      if (!revision.permitida) {
        if (alive.current) { setFicha({ ...ficha, visita: v, reglas });  setError(revision.mensaje); }
        return;
      }
      const auth = await token();
      enviado = true;
      const scope = `?condominio_id=${encodeURIComponent(condominioId)}`;
      if (operacion === "entrada" && ficha.qr) {
        await api.get(`/qr/validar/${encodeURIComponent(v.visita_id)}/${encodeURIComponent(ficha.qr)}${scope}`, auth, AbortSignal.timeout(20000));
      } else {
        await api.patch(`/visitas/${encodeURIComponent(v.visita_id)}/${operacion}${scope}`, {}, auth, AbortSignal.timeout(20000));
      }
      const actual = await detalle(v.visita_id);
      if (!await cerrar(actual, operacion)) throw new Error("El servidor aún no confirma el movimiento.");
    } catch (e) {
      if (!alive.current) return;
      if (enviado) {
        try { if (await cerrar(await detalle(ficha.visita.visita_id), operacion)) return; } catch { /* Resolve with a read before permitting a retry. */ }
        setIncierto(true);
        setError("No pudimos confirmar el movimiento. Pulsa Comprobar registro antes de hacer cualquier otro intento.");
      } else setError("No pudimos comprobar la visita antes de registrar. Actualiza la revisión e intenta de nuevo.");
      if (e instanceof Error && !/fetch|timeout|abort|network/i.test(e.message)) setError(prev => `${prev} Motivo: ${e.message}`);
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  if (exito) return <section role="status" className="rounded-2xl border border-emerald-500 bg-emerald-950/40 p-6 text-center space-y-4">
    <h2 className="text-2xl font-bold text-emerald-200">{exito.op === "entrada" ? "Entrada registrada" : "Salida registrada"}</h2>
    <p className="text-xl">{exito.nombre}</p><p>El movimiento quedó guardado en AXS.</p>
    {foto && <div className="space-y-3">
      {busy && <p role="status">Guardando foto de salida…</p>}
      {fotoGuardada && <p role="status">Foto de salida guardada.</p>}
      {fotoError && <><p role="alert" className="text-amber-200">{fotoError}</p><button disabled={busy} className={button} onClick={reintentarFoto}>Reintentar foto</button></>}
    </div>}
    <button disabled={busy} className={button} onClick={() => reset()}>Atender a la siguiente persona</button>
    <p className="text-sm text-gray-300">{foto ? fotoError ? "Puedes continuar sin confirmar la foto. La salida no se pierde." : "Puedes continuar con la siguiente persona." : "Volveremos al inicio en unos segundos."}</p>
  </section>;
  return <section className="space-y-5" aria-label="Operación de caseta">
    <div className="grid grid-cols-2 gap-3" aria-label="Tipo de movimiento">
      {(["entrada", "salida"] as const).map(op => <button key={op} type="button"
        className={`min-h-24 w-full rounded-2xl border-2 border-gray-600 px-4 py-6 text-2xl font-bold focus-visible:outline-2 focus-visible:outline-purple-400 disabled:opacity-50 ${abierto && operacion === op ? op === "entrada" ? "bg-emerald-900/40 text-emerald-200 border-emerald-500" : "bg-purple-900/40 text-purple-200 border-purple-500" : "hover:bg-gray-800"}`}
        aria-expanded={abierto && operacion === op} aria-controls={panelId} disabled={busy || incierto}
        onClick={() => { if (operacion === op) setAbierto(value => !value); else reset(op); }}>
        {op === "entrada" ? "Entrada" : "Salida"}<span aria-hidden="true" className="ml-2">{abierto && operacion === op ? "▴" : "▾"}</span>
      </button>)}
    </div>
    <div id={panelId} hidden={!abierto} className="space-y-5">
    {abierto && <>
    {!destino ? <GuardiaDestino key={operacion} condominioId={condominioId} salida={operacion === "salida"} onSelect={casa => { setDestino(casa); setManual(true); }} /> : <>
      <div className="rounded-xl border border-purple-500 bg-purple-950/30 p-4">
        <p className="text-sm text-purple-200">{operacion === "entrada" ? "Viene a" : "Viene de"}</p>
        <p className="text-xl font-bold">{nombreDestino(destino)}</p>
        <p className="text-gray-300">{(destino.residentes ?? (destino.residente ? [destino.residente] : [])).map(r => r.nombre).filter(Boolean).join(" · ")}</p>
        <button disabled={busy || incierto} className="mt-3 min-h-11 text-purple-200 underline" onClick={() => reset(operacion)}>Cambiar casa o persona visitada</button>
      </div>
      {error && <p role="alert" className="rounded-xl border border-amber-700 bg-amber-950/30 p-4 text-amber-100">{error}</p>}
      {busy && <p role="status">Comprobando con AXS…</p>}
      {operacion === "entrada" && !busy && !incierto && !camara && !ficha?.visita.qr_token && ["casa", "depto", "local"].includes(destino.tipo) && <SolicitudesAcceso
        key={`${condominioId}:${destino.casa_id}:${ficha?.visita.visita_id ?? "nueva"}`}
        condominioId={condominioId} destinoId={destino.casa_id} visita={ficha?.visita}
        onRevisar={id => { void revisar(id); }} /> }
      {camara ? <GuardiaQrScanner onRead={leerQR} onCancel={() => { setCamara(false); setManual(true); }} /> : ficha ? <article className="space-y-4 rounded-2xl border border-gray-700 bg-gray-900 p-5">
        <p className="text-sm text-purple-200">Confirma esta visita</p>
        <h3 className="text-2xl font-bold">{ficha.visita.nombre_visitante}</h3>
        <p className="text-xl">Destino: {ficha.visita.casa_unidad}</p>
        {ficha.visita.placa && <p className="text-lg">Placa registrada: {ficha.visita.placa}</p>}
        {ficha.visita.proposito && <p className="text-gray-300">Viene por: {ficha.visita.proposito}</p>}
        <p className={resultado?.permitida ? "text-emerald-200" : "text-amber-200"}>{resultado?.mensaje}</p>
        <IdentificacionVisita key={ficha.visita.visita_id} visitaId={ficha.visita.visita_id} condominioId={condominioId} nombreInvitado={ficha.visita.nombre_visitante} />
        {ficha.visita.salida_registrada_en && <EvidenciaSalida key={`salida:${ficha.visita.visita_id}`} visitaId={ficha.visita.visita_id} condominioId={condominioId} />}
        {operacion === "salida" && resultado?.permitida && !incierto && <>
          {!ficha.reglas ? <p className="text-sm text-amber-200">No se pudo consultar la opción de foto. Puedes registrar la salida o actualizar la revisión.</p> : ficha.reglas.foto_salida !== "deshabilitada" && <div className="space-y-3 rounded-xl border border-gray-600 p-4">
            <p className="font-semibold">Evidencia de salida (opcional)</p>
            {(fotoAbierta || ficha.reglas.foto_salida === "siempre_visible") ? <>
              <label className="block">Tomar o seleccionar foto
                <input key={foto?.captura ?? "empty-photo"} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" disabled={busy}
                  className="block min-h-12 w-full py-3" onChange={e => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (file.size > 8 * 1024 * 1024) { setFotoError("La foto debe pesar como máximo 8 MB."); e.target.value = ""; setFoto(null); return; }
                    setFoto({ file, captura: crypto.randomUUID() }); setFotoError(""); setFotoGuardada(false);
                  }} />
              </label>
              <p className="text-sm text-gray-300">Se adjuntará al confirmar la salida. Puedes continuar sin fotografía.</p>
            </> : <button disabled={busy} className={button} onClick={() => setFotoAbierta(true)}>Agregar foto</button>}
            {foto && <><VistaFotoSalida file={foto.file} /><button disabled={busy} className={button} onClick={() => { setFoto(null); setFotoError(""); }}>Quitar foto</button></>}
            {fotoError && <p role="alert" className="text-amber-200">{fotoError}</p>}
          </div>}
        </>}
        {incierto ? <button disabled={busy} className={`${button} w-full bg-amber-900/40`} onClick={comprobar}>Comprobar registro</button> : <>
          {resultado?.permitida && <button disabled={busy} className={`${button} w-full bg-emerald-800 text-white`} onClick={registrar}>Confirmar {operacion} de {ficha.visita.nombre_visitante}</button>}
          <div className="flex flex-wrap gap-2"><button disabled={busy} className={button} onClick={() => revisar(ficha.visita.visita_id, ficha.qr)}>Actualizar revisión</button><button disabled={busy} className={button} onClick={() => { setFicha(null);  setError(""); }}>Buscar otra visita</button></div>
        </>}
      </article> : <>
        <h2 className="text-2xl font-bold">¿Cómo se llama el visitante?</h2>
        <div className="grid grid-cols-2 gap-3"><button disabled={busy} className={`${button} bg-purple-800`} onClick={() => { setError(""); setCamara(true); }}>Escanear QR</button><button disabled={busy} className={button} onClick={() => { setManual(true); setError(""); }}>Buscar por nombre</button></div>
        {manual && <form onSubmit={e => { e.preventDefault(); void buscar(); }} className="space-y-3">
          <label className="block" htmlFor="buscar-visita">Nombre del visitante o placa</label>
          <input id="buscar-visita" autoFocus autoComplete="off" value={consulta} onChange={e => { setConsulta(e.target.value); setRows(null); }} placeholder="Ej. Juan Pérez" className="min-h-12 w-full rounded-xl border border-gray-600 bg-gray-900 px-4" />
          <button disabled={busy || consulta.trim().length < 2} className={`${button} w-full`}>Buscar visita</button>
          <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={historial} onChange={e => setHistorial(e.target.checked)} />No lo encuentro: revisar otros registros de esta casa</label>
          <p className="text-xs text-gray-400">{historial ? "Consulta del historial del condominio seleccionado." : operacion === "salida" ? "Buscamos primero entre visitas que entraron y aún no tienen salida, incluso de días anteriores." : "Buscamos visitas pendientes de entrada."}</p>
        </form>}
        {rows && <div className="space-y-3" aria-label="Coincidencias de visitas">
          <p role="status">Elige al visitante que tienes enfrente.</p>
          {coincidencias.slice(0, 8).map(v => <button disabled={busy} key={v.visita_id} className={`${button} w-full text-left`} onClick={() => revisar(v.visita_id)}>
            <span className="block text-lg">{v.nombre_visitante} · {v.casa_unidad}{v.placa ? ` · ${v.placa}` : ""}</span>
            <span className="block text-sm font-normal">{v.salida_registrada_en ? "Ya salió" : v.entrada_registrada_en ? "Tiene entrada registrada" : "Visita pendiente de entrada"}{v.proposito ? ` · ${v.proposito}` : ""}</span>
          </button>)}
          {coincidencias.length > 8 && <p>Hay más coincidencias. Agrega el nombre y la vivienda para precisar la búsqueda.</p>}
          {coincidencias.length === 0 && <p className="text-amber-200">No aparece una visita para esta persona en el destino elegido. Confirma su nombre y consulta al residente o a administración.</p>}
        </div>}
        <details><summary className="cursor-pointer py-3 text-sm text-gray-300">Usar lector QR o pegar código</summary><form className="space-y-3" onSubmit={e => { e.preventDefault(); leerQR(codigo); }}><label htmlFor="codigo-qr">Código AXS</label><input id="codigo-qr" value={codigo} onChange={e => setCodigo(e.target.value)} autoComplete="off" className="min-h-12 w-full rounded-xl border border-gray-600 bg-gray-900 px-3" /><button disabled={busy || !codigo} className={button}>Revisar QR</button></form></details>
        {operacion === "entrada" && <details><summary className="cursor-pointer py-3 text-sm text-gray-300">La visita no tiene registro previo</summary><p className="mb-3 text-sm">Contacta al residente o a administración. Si las reglas permiten registro en caseta, puedes usar el formulario; no sustituye una autorización ni un QR requeridos.</p><a className={`${button} inline-block`} href={`/dashboard/guardia/nueva?destino=${encodeURIComponent(destino.casa_id)}&condominio=${encodeURIComponent(condominioId)}`}>Abrir registro en caseta</a></details>}
      </>}
    </>}
    </>}
    </div>
  </section>;
}
