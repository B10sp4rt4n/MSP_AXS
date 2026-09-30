"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

interface QRResult {
  visita_id: string;
  qr_base64: string;
  qr_vigencia: string;
  qr_inicio: string | null;
}

export default function PreregistroClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [form, setForm] = useState({
    nombre_visitante: "",
    fecha_visita: "",
    tipo_visita: "visita_personal",
    placa: "",
    notas: "",
  });
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
        nombre_visitante: form.nombre_visitante,
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
          <button onClick={() => router.push("/dashboard/residente")} className="text-gray-400 hover:text-white">←</button>
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
              onClick={() => router.push("/dashboard/residente")}
              className="w-full bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl text-sm"
            >
              Volver a mis visitas
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

          <button type="submit" disabled={loading || !horaServidor}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-xl text-sm mt-2"
          >
            {loading ? "Generando QR..." : "Generar QR de Acceso"}
          </button>
        </form>
      </main>
    </div>
  );
}
