"use client";

import { UserButton, useUser } from "@clerk/nextjs";

export default function DashboardClient() {
  const { user } = useUser();

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">AX-S MSP</h1>
          <p className="text-xs text-gray-400">Control de Acceso</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-300">
            {user?.firstName ?? user?.emailAddresses[0]?.emailAddress}
          </span>
          <UserButton />
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <DashCard title="Portal Guardia" href="/dashboard/guardia" icon="🛡️"
            desc="Registrar entradas, salidas y validar QR" />
          <DashCard title="Portal Residente" href="/dashboard/residente" icon="🏠"
            desc="Preregistrar visitas y generar QR de acceso" />
          <DashCard title="Panel Admin" href="/dashboard/admin" icon="⚙️"
            desc="Visitas, casas y usuarios del condominio" />
        </div>
      </main>
    </div>
  );
}

function DashCard({ title, href, icon, desc }: {
  title: string; href: string; icon: string; desc: string;
}) {
  return (
    <a href={href}
      className="block p-5 rounded-xl border border-gray-700 bg-gray-900 hover:border-blue-500 hover:bg-gray-800 transition-all">
      <div className="text-3xl mb-3">{icon}</div>
      <h2 className="font-semibold text-white">{title}</h2>
      <p className="text-sm text-gray-400 mt-1">{desc}</p>
    </a>
  );
}
