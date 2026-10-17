"use client";
import { useEffect, useRef, useState } from "react";

export default function GuardiaQrScanner({ onRead, onCancel }: { onRead: (value: string) => void; onCancel: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let stopped = false, frame = 0;
    let stream: MediaStream | null = null;
    const stop = () => { stopped = true; cancelAnimationFrame(frame); stream?.getTracks().forEach(t => t.stop()); };
    async function start() {
      try {
        const jsQR = (await import("jsqr")).default;
        if (stopped) return;
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (stopped) { stream.getTracks().forEach(t => t.stop()); return; }
        if (!video.current) return;
        video.current.srcObject = stream;
        await video.current.play();
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        const scan = () => {
          if (stopped || !video.current || !ctx) return;
          if (video.current.readyState >= 2) {
            canvas.width = video.current.videoWidth; canvas.height = video.current.videoHeight;
            ctx.drawImage(video.current, 0, 0);
            const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const qr = jsQR(pixels.data, pixels.width, pixels.height);
            if (qr?.data) { stop(); onRead(qr.data); return; }
          }
          frame = requestAnimationFrame(scan);
        };
        scan();
      } catch { stop(); setError("No pudimos abrir la cámara. Permite su uso o vuelve a buscar sin QR."); }
    }
    void start();
    return stop;
  }, [onRead]);
  return <div className="space-y-3">
    <p>Apunta al QR. Primero revisaremos la visita; todavía no se registra ningún movimiento.</p>
    {error && <p role="alert" className="text-amber-200">{error}</p>}
    <video ref={video} muted playsInline className="w-full rounded-xl bg-black" />
    <button type="button" className="min-h-12 w-full rounded-xl border border-gray-600" onClick={onCancel}>Volver / Sin QR</button>
  </div>;
}
