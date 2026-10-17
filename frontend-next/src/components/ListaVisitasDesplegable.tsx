"use client";

import { useId, useState, type ReactNode } from "react";

export default function ListaVisitasDesplegable({ children }: { children: ReactNode }) {
  const [visible, setVisible] = useState(true);
  const panelId = useId();

  return (
    <section className="space-y-3" aria-label="Lista de visitas">
      <button
        type="button"
        aria-expanded={visible}
        aria-controls={panelId}
        onClick={() => setVisible(value => !value)}
        className="min-h-11 rounded-lg border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-400"
      >
        {visible ? "Ocultar lista de visitas" : "Mostrar lista de visitas"}
      </button>
      {!visible && <p className="text-xs text-gray-400">Lista oculta. Tus registros se conservan y puedes volver a mostrarlos aquí.</p>}
      <div id={panelId} hidden={!visible}>{children}</div>
    </section>
  );
}
