"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type ResultadoQR = {
  status: string;
  visita_id: string;
  nombre_visitante: string;
  casa_unidad: string;
  condominio_id: string;
};

export default function ValidarQRClient() {
  const router = useRouter();
  const { getToken } = useAuth();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animRef = useRef<number>(0);

  const [escaneando, setEscaneando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoQR | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const detener = useCallback(() => {
    cancelAnimationFrame(animRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setEscaneando(false);
  }, []);

  const procesarQR = useCallback(async (texto: string) => {
    const partes = texto.split("|");
    if (partes.length !== 3 || partes[0] !== "AXS") {
      setError("QR no reconocido. Debe ser un QR generado por AX-S.");
      return;
    }
    const [, visita_id, token] = partes;
    setLoading(true);
    try {
      const authToken = await getToken();
      const res = await api.get<ResultadoQR>(`/qr/validar/${visita_id}/${token}`, authToken!);
      setResultado(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("400")) setError("QR inválido, expirado o ya utilizado.");
      else if (msg.includes("404")) setError("Visita no encontrada.");
      else setError("Error al validar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!escaneando) return;

    let stopped = false;

    const arrancar = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" }
        });
        if (stopped) { stream.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        escanearFrame();
      } catch {
        setError("No se pudo acceder a la cámara. Verifica los permisos.");
        setEscaneando(false);
      }
    };

    const escanearFrame = async () => {
      if (stopped || !videoRef.current || !canvasRef.current) return;
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video.readyState !== video.HAVE_ENOUGH_DATA) {
        animRef.current = requestAnimationFrame(escanearFrame);
        return;
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      const jsQR = (await import("jsqr")).default;
      const code = jsQR(imageData.data, imageData.width, imageData.height);
      if (code?.data) {
        stopped = true;
        detener();
        await procesarQR(code.data);
        return;
      }
      animRef.current = requestAnimationFrame(escanearFrame);
    };

    arrancar();

    return () => {
      stopped = true;
      cancelAnimationFrame(animRef.current);
      streamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, [escaneando, detener, procesarQR]);

  const reiniciar = () => { setResultado(null); setError(""); };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center gap-3">
        <button onClick={() => { detener(); router.push("/dashboard/guardia"); }}
          className="text-gray-400 hover:text-white text-sm">
          ← Guardia
        </button>
        <h1 className="text-lg font-bold">Validar QR</h1>
      </header>

      <main className="p-4 max-w-sm mx-auto">

        {/* Resultado aprobado */}
        {resultado && (
          <div className="text-center mt-8">
            <div className="bg-green-900/40 border border-green-500 rounded-2xl p-8 mb-6">
              <p className="text-6xl mb-4">✅</p>
              <p className="text-2xl font-bold text-green-400 mb-4">Acceso Aprobado</p>
              <p className="text-white text-xl font-semibold">{resultado.nombre_visitante}</p>
              <p className="text-gray-400 mt-1">Casa {resultado.casa_unidad}</p>
              <p className="text-gray-500 text-xs mt-2">Entrada registrada</p>
            </div>
            <button onClick={reiniciar}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl">
              Escanear otro QR
            </button>
          </div>
        )}

        {/* Error */}
        {!resultado && error && (
          <div className="text-center mt-8">
            <div className="bg-red-900/40 border border-red-500 rounded-2xl p-8 mb-6">
              <p className="text-6xl mb-4">❌</p>
              <p className="text-xl font-bold text-red-400 mb-2">Acceso Denegado</p>
              <p className="text-gray-300 text-sm">{error}</p>
            </div>
            <button onClick={reiniciar}
              className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-xl">
              Intentar de nuevo
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && !resultado && !error && (
          <div className="text-center py-16">
            <p className="text-gray-400">Validando acceso...</p>
          </div>
        )}

        {/* Scanner / Inicio */}
        {!resultado && !error && !loading && (
          <>
            {/* Video en vivo */}
            <div className={escaneando ? "block" : "hidden"}>
              <p className="text-sm text-gray-400 text-center mb-3">
                Apunta la cámara al QR del visitante
              </p>
              <div className="relative rounded-xl overflow-hidden bg-black">
                <video ref={videoRef} className="w-full" playsInline muted />
                {/* Guía visual */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-52 h-52 border-2 border-white/60 rounded-xl" />
                </div>
              </div>
              <canvas ref={canvasRef} className="hidden" />
              <button onClick={detener}
                className="w-full mt-4 bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl text-sm">
                Cancelar
              </button>
            </div>

            {/* Pantalla inicial */}
            {!escaneando && (
              <div className="text-center pt-16">
                <p className="text-7xl mb-6">📷</p>
                <p className="text-gray-400 text-sm mb-10">
                  Escanea el QR que generó el residente para autorizar la entrada
                </p>
                <button onClick={() => setEscaneando(true)}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl text-lg">
                  Abrir cámara
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
