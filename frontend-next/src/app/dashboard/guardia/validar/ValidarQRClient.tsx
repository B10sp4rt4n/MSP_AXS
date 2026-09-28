"use client";

import { useEffect, useRef, useState } from "react";
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
  const scannerRef = useRef<HTMLDivElement>(null);
  const [escaneando, setEscaneando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoQR | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const html5QrRef = useRef<any>(null);

  const iniciarScanner = async () => {
    setError("");
    setResultado(null);
    setEscaneando(true);
  };

  useEffect(() => {
    if (!escaneando || !scannerRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let scanner: any = null;

    const arrancar = async () => {
      const { Html5Qrcode } = await import("html5-qrcode");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      scanner = new Html5Qrcode("qr-reader") as any;
      html5QrRef.current = scanner;

      try {
        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          async (texto: string) => {
            // Detener scanner al leer
            await scanner!.stop();
            setEscaneando(false);
            await procesarQR(texto);
          },
          () => {}
        );
      } catch {
        setError("No se pudo acceder a la cámara. Verifica los permisos.");
        setEscaneando(false);
      }
    };

    arrancar();

    return () => {
      scanner?.stop().catch(() => {});
    };
  }, [escaneando]);

  const procesarQR = async (texto: string) => {
    // Formato esperado: AXS|{visita_id}|{token}
    const partes = texto.split("|");
    if (partes.length !== 3 || partes[0] !== "AXS") {
      setError("QR no reconocido. Debe ser un QR generado por AX-S.");
      return;
    }

    const [, visita_id, token] = partes;
    setLoading(true);
    setError("");

    try {
      const authToken = await getToken();
      const res = await api.get<ResultadoQR>(
        `/qr/validar/${visita_id}/${token}`,
        authToken!
      );
      setResultado(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al validar QR";
      if (msg.includes("400")) setError("QR inválido, expirado o ya utilizado.");
      else if (msg.includes("404")) setError("Visita no encontrada.");
      else setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const reiniciar = () => {
    setResultado(null);
    setError("");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center gap-3">
        <button onClick={() => router.push("/dashboard/guardia")} className="text-gray-400 hover:text-white text-sm">
          ← Guardia
        </button>
        <h1 className="text-lg font-bold">Validar QR</h1>
      </header>

      <main className="p-4 max-w-sm mx-auto">
        {/* Resultado aprobado */}
        {resultado && (
          <div className="text-center">
            <div className="bg-green-900/40 border border-green-500 rounded-2xl p-8 mb-6">
              <p className="text-6xl mb-4">✅</p>
              <p className="text-2xl font-bold text-green-400 mb-1">Acceso Aprobado</p>
              <p className="text-gray-300 text-lg font-semibold mt-4">{resultado.nombre_visitante}</p>
              <p className="text-gray-400 text-sm mt-1">Casa {resultado.casa_unidad}</p>
              <p className="text-gray-500 text-xs mt-1">Entrada registrada</p>
            </div>
            <button
              onClick={reiniciar}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl"
            >
              Escanear otro QR
            </button>
          </div>
        )}

        {/* Error */}
        {!resultado && error && (
          <div className="text-center">
            <div className="bg-red-900/40 border border-red-500 rounded-2xl p-8 mb-6">
              <p className="text-6xl mb-4">❌</p>
              <p className="text-xl font-bold text-red-400 mb-2">Acceso Denegado</p>
              <p className="text-gray-300 text-sm">{error}</p>
            </div>
            <button
              onClick={reiniciar}
              className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-xl"
            >
              Intentar de nuevo
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <p className="text-gray-400">Validando...</p>
          </div>
        )}

        {/* Scanner */}
        {!resultado && !error && !loading && (
          <>
            {escaneando ? (
              <div>
                <p className="text-sm text-gray-400 text-center mb-3">
                  Apunta la cámara al QR del visitante
                </p>
                <div
                  id="qr-reader"
                  ref={scannerRef}
                  className="rounded-xl overflow-hidden"
                />
                <button
                  onClick={async () => {
                    await html5QrRef.current?.stop().catch(() => {});
                    setEscaneando(false);
                  }}
                  className="w-full mt-4 bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl text-sm"
                >
                  Cancelar
                </button>
              </div>
            ) : (
              <div className="text-center pt-12">
                <p className="text-6xl mb-6">📷</p>
                <p className="text-gray-400 text-sm mb-8">
                  Escanea el QR que generó el residente para autorizar la entrada
                </p>
                <button
                  onClick={iniciarScanner}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl text-lg"
                >
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
