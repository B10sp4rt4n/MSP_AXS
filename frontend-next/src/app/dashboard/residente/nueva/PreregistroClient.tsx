"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { CampoProposito, useReglasAcceso } from "@/components/ReglasAcceso";
import { api } from "@/lib/api";

interface QRResult {
  visita_id: string;
  qr_base64: string;
  qr_vigencia: string;
  qr_inicio: string | null;
}

export default function PreregistroClient() {
  const { userId } = useAuth();
  return <PreregistroForm key={userId ?? "signed-out"} />;
}

function PreregistroForm() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [form, setForm] = useState({
    nombre_visitante: "",
    proposito: "",
    fecha_visita: "",
    tipo_visita: "visita_personal",
    placa: "",
    notas: "",
  });
  const [perfil, setPerfil] = useState<{ rol: string; condominio_id: string | null } | null>(null);
  const [perfilError, setPerfilError] = useState("");
  const [condominios, setCondominios] = useState<{ condominio_id: string; nombre: string }[]>([]);
  const [condominioId, setCondominioId] = useState("");
  const [destinoId, setDestinoId] = useState("");
  const [catalogo, setCatalogo] = useState<{ tenant: string; destinos: { destino_id: string; nombre: string }[]; error: string } | null>(null);
  const administrativo = perfil?.rol === "MSP_ADMIN" || perfil?.rol === "ADMIN_CONDOMINIO";
  const permitido = administrativo || perfil?.rol === "RESIDENTE";
  const tenant = administrativo ? condominioId : perfil?.condominio_id ?? "";
  const destinos = catalogo?.tenant === condominioId ? catalogo.destinos : [];
  const catalogError = catalogo?.tenant === condominioId ? catalogo.error : "";
  const destinoValido = destinos.some(d => d.destino_id === destinoId);
  const { reglas, error: reglasError } = useReglasAcceso(tenant);

  useEffect(() => {
    let active = true;
    async function cargar() {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const me = await api.get<{ rol: string; condominio_id: string | null }>("/auth/me", token);
      const condos = ["MSP_ADMIN", "ADMIN_CONDOMINIO"].includes(me.rol)
        ? await api.get<{ condominio_id: string; nombre: string }[]>("/condominios/", token) : [];
      if (active) { setPerfil(me); setCondominios(condos); }
    }
    cargar().catch(e => { if (active) setPerfilError(e instanceof Error ? e.message : "No se pudo verificar tu cuenta"); });
    return () => { active = false; };
  }, [getToken]);

  useEffect(() => {
    let active = true;
    if (!administrativo || !condominioId) return;
    async function cargar() {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const data = await api.get<{ destino_id: string; nombre: string }[]>(`/condominios/${encodeURIComponent(condominioId)}/destinos`, token);
      if (active) setCatalogo({ tenant: condominioId, destinos: data, error: "" });
    }
    cargar().catch(e => { if (active) setCatalogo({ tenant: condominioId, destinos: [], error: e instanceof Error ? e.message : "No se pudieron cargar los destinos" }); });
    return () => { active = false; };
  }, [administrativo, condominioId, getToken]);
  const requiereProposito = !!(reglas?.exigir_proposito && reglas.tipos_visita.includes(form.tipo_visita));
  const [programada, setProgramada] = useState(false);
  const [horaServidor, setHoraServidor] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [qr, setQr] = useState<QRResult | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | undefined;
    getToken().then(token => api.get<{ utc: string }>("/preregistro/reloj", token!))
      .then(({ utc }) => {
        if (!active) return;
        const origin = Date.parse(utc);
        const elapsedStart = performance.now();
        const update = () => {
          const now = new Date(origin + performance.now() - elapsedStart);
          const pad = (value: number) => String(value).padStart(2, "0");
          setHoraServidor(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`);
        };
        update();
        timer = setInterval(update, 1000);
      }).catch(() => { if (active) setError("No se pudo consultar la hora del servidor. Recarga la página."); });
    return () => { active = false; if (timer) clearInterval(timer); };
  }, [getToken]);

  const set = (field: string, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || !permitido || !reglas || reglasError || !tenant || (administrativo && !destinoValido)) {
      setError("Verifica el condominio, destino y reglas antes de continuar.");
      return;
    }
    const fechaVisita = new Date(form.fecha_visita);
    if (programada && (!Number.isFinite(fechaVisita.getTime()) || fechaVisita.getTime() <= new Date(horaServidor).getTime())) {
      setError("La fecha y hora de visita deben ser posteriores a la hora actual.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getToken();
      const payload = {
        ...(administrativo ? { condominio_id: condominioId, destino_id: destinoId } : {}),
        nombre_visitante: form.nombre_visitante,
        proposito: form.proposito || undefined,
        fecha_visita: programada ? fechaVisita.toISOString() : undefined,
        tipo_visita: form.tipo_visita,
        placa: form.placa || undefined,
        notas: form.notas || undefined,
      };
      const result = await api.post<QRResult>("/preregistro/crear", payload, token!);
      setQr(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear preregistro");
    } finally {
      setLoading(false);
    }
  };

  const compartirWhatsApp = async () => {
    if (!qr) return;
    const texto = `🏠 *Preregistro de visita*\n\nVisitante: ${form.nombre_visitante}\nAcceso: ${qr.qr_inicio ? new Date(qr.qr_inicio).toLocaleString("es-MX") : "Ahora"} — ${new Date(qr.qr_vigencia).toLocaleString("es-MX")}\nID: ${qr.visita_id}\n\nPresenta este código QR al guardia al llegar.`;

    // Intentar Web Share API (soporta imagen en móvil)
    if (navigator.canShare) {
      try {
        const blob = await fetch(`data:image/png;base64,${qr.qr_base64}`).then(r => r.blob());
        const file = new File([blob], "qr-visita.png", { type: "image/png" });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file], text: texto, title: "QR de visita" });
          return;
        }
      } catch {
        // fall through to text share
      }
    }
    // Fallback: compartir solo texto
    window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`, "_blank");
  };

  const descargarQR = () => {
    if (!qr) return;
    const a = document.createElement("a");
    a.href = `data:image/png;base64,${qr.qr_base64}`;
    a.download = `qr-${form.nombre_visitante.replace(/\s+/g, "-")}.png`;
    a.click();
  };

  if (qr) {
    return (
      <div className="min-h-screen bg-gray-950 text-white">
        <header className="border-b border-gray-800 px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push(administrativo ? "/dashboard" : "/dashboard/residente")} className="text-gray-400 hover:text-white">←</button>
          <h1 className="text-lg font-bold">QR Generado</h1>
        </header>
        <main className="p-4 max-w-sm mx-auto text-center">
          <div className="mt-6 bg-white rounded-2xl p-4 inline-block">
            <img src={`data:image/png;base64,${qr.qr_base64}`} alt="QR Code" className="w-56 h-56" />
          </div>
          <p className="mt-4 font-semibold text-white">{form.nombre_visitante}</p>
          <p className="text-sm text-gray-400 mt-1">
            {qr.qr_inicio && <>Válido desde: {new Date(qr.qr_inicio).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })}<br /></>}
            Válido hasta: {new Date(qr.qr_vigencia).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })}
          </p>
          <div className="mt-6 space-y-3">
            <button
              onClick={compartirWhatsApp}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-xl text-sm"
            >
              Compartir QR por WhatsApp
            </button>
            <button
              onClick={descargarQR}
              className="w-full bg-blue-700 hover:bg-blue-800 text-white font-semibold py-3 rounded-xl text-sm"
            >
              Descargar QR
            </button>
            <button
              onClick={() => router.push(administrativo ? "/dashboard" : "/dashboard/residente")}
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl text-sm"
            >
              Volver al panel
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center gap-3">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-white">←</button>
        <h1 className="text-lg font-bold">Preregistrar Visita</h1>
      </header>

      <main className="p-4 max-w-md mx-auto">
        <form onSubmit={submit} className="space-y-4 mt-2">
          {perfilError && <p role="alert">{perfilError}</p>}
          {!perfil && !perfilError && <p role="status">Verificando cuenta…</p>}
          {perfil && !permitido && <p role="alert">Tu rol no permite preregistrar visitas.</p>}
          {administrativo && <fieldset disabled={loading} className="space-y-3">
            <legend>Preregistro administrativo</legend>
            <label className="block">Condominio
              <select aria-label="Condominio" required value={condominioId} onChange={e => {
                setCondominioId(e.target.value); setDestinoId(""); setCatalogo(null); setError("");
              }} className="block w-full bg-gray-800 rounded p-2">
                <option value="">Selecciona un condominio</option>
                {condominios.map(c => <option key={c.condominio_id} value={c.condominio_id}>{c.nombre}</option>)}
              </select>
            </label>
            <label className="block">Destino
              <select aria-label="Destino" required disabled={!condominioId || catalogo?.tenant !== condominioId || !!catalogError}
                value={destinoId} onChange={e => setDestinoId(e.target.value)} className="block w-full bg-gray-800 rounded p-2">
                <option value="">Selecciona vivienda, administración o área común</option>
                {destinos.map(d => <option key={d.destino_id} value={d.destino_id}>{d.nombre}</option>)}
              </select>
            </label>
            <p className="text-sm text-gray-400">La autorización quedará registrada a tu nombre para el destino seleccionado.</p>
            {catalogError && <p role="alert">{catalogError}</p>}
          </fieldset>}
          {reglasError && <p role="alert">{reglasError}</p>}

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Nombre del visitante *</label>
            <input required type="text" placeholder="Ej. Juan Pérez"
              value={form.nombre_visitante} onChange={(e) => set("nombre_visitante", e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm text-gray-300 mb-3">
              <input type="checkbox" checked={programada} onChange={e => {
                setProgramada(e.target.checked);
                if (e.target.checked) set("fecha_visita", horaServidor);
              }} />
              Programar para otra fecha
            </label>
            <label className="text-xs text-gray-400 mb-1 block">
              {programada ? "Fecha y hora de visita (hora local) *" : "Fecha y hora del servidor (hora local)"}
            </label>
            <input required={programada} readOnly={!programada} type="datetime-local"
              value={programada ? form.fecha_visita : horaServidor} onChange={(e) => set("fecha_visita", e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <p className="text-xs text-gray-400">
            {programada ? "Acceso desde 30 minutos antes hasta 60 minutos después de la visita." : "Visita inmediata: hora fijada por el servidor y QR válido durante 60 minutos."}
          </p>

          <CampoProposito value={form.proposito} onChange={v => set("proposito", v)} required={requiereProposito} />
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Tipo de visita</label>
            <div className="grid grid-cols-3 gap-2">
              {["visita_personal", "proveedor", "entrega"].map((tipo) => (
                <button key={tipo} type="button" onClick={() => set("tipo_visita", tipo)}
                  className={`py-2 rounded-lg text-xs font-medium border transition-all ${
                    form.tipo_visita === tipo
                      ? "bg-blue-600 border-blue-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500"
                  }`}
                >
                  {tipo === "visita_personal" ? "Personal" : tipo === "proveedor" ? "Proveedor" : "Entrega"}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Placa (opcional)</label>
            <input type="text" placeholder="Ej. ABC-123"
              value={form.placa} onChange={(e) => set("placa", e.target.value.toUpperCase())}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Notas (opcional)</label>
            <textarea placeholder="Ej. Viene a entregar paquete"
              value={form.notas} onChange={(e) => set("notas", e.target.value)}
              rows={2}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          {error && <p role="alert" className="text-red-400 text-sm">{error}</p>}

          <button type="submit" disabled={loading || !horaServidor || !permitido || !tenant || !reglas || !!reglasError || (administrativo && !destinoValido)}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-xl text-sm mt-2"
          >
            {loading ? "Generando QR..." : "Generar QR de Acceso"}
          </button>
        </form>
      </main>
    </div>
  );
}
