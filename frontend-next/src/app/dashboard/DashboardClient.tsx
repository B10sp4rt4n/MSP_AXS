"use client";

import { useEffect, useState } from "react";
import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import { api } from "@/lib/api";

interface MeResponse {
  rol: string;
  nombre: string;
  email: string;
  condominio_id: string | null;
  casa_unidad: string | null;
}

const PORTALES: {
  title: string;
  href: string;
  icon: string;
  desc: string;
  roles: string[];
}[] = [
  {
    title: "Portal Guardia",
    href: "/dashboard/guardia",
    icon: "🛡️",
    desc: "Registrar entradas, salidas y validar QR",
    roles: ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"],
  },
  {
    title: "Portal Residente",
    href: "/dashboard/residente",
    icon: "🏠",
    desc: "Preregistrar visitas y generar QR de acceso",
    roles: ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"],
  },
  {
    title: "Panel Admin",
    href: "/dashboard/admin",
    icon: "⚙️",
    desc: "Visitas, casas y usuarios del condominio",
    roles: ["ADMIN_CONDOMINIO", "MSP_ADMIN"],
  },
  {
    title: "Dashboard MSP",
    href: "/dashboard/msp",
    icon: "🏢",
    desc: "Vista global de condominios y usuarios del sistema",
    roles: ["MSP_ADMIN"],
  },
];

export default function DashboardClient() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    getToken()
      .then((token) => token ? api.get<MeResponse>("/auth/me", token) : null)
      .then((data) => { if (data) setMe(data); })
      .catch(() => {});
  }, [getToken]);

  const portales = me
    ? PORTALES.filter((p) => p.roles.includes(me.rol))
    : PORTALES; // mientras carga, muestra todos (fallback graceful)

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">AX-S MSP</h1>
          <p className="text-xs text-gray-400">Control de Acceso</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm text-gray-300">
              {me?.nombre ?? user?.firstName ?? user?.emailAddresses[0]?.emailAddress}
            </p>
            {me?.rol && (
              <p className="text-xs text-gray-500">{me.rol.replace("_", " ")}</p>
            )}
          </div>
          <UserButton />
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        {me?.condominio_id === null && me?.rol === "RESIDENTE" && (
          <div className="mb-4 bg-yellow-900/30 border border-yellow-700 rounded-xl p-4 text-sm text-yellow-300">
            Tu cuenta aún no tiene una casa asignada. Contacta al administrador de tu condominio.
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {portales.map((p) => (
            <DashCard key={p.href} title={p.title} href={p.href} icon={p.icon} desc={p.desc} />
          ))}
        </div>
      </main>
    </div>
  );
}

function DashCard({ title, href, icon, desc }: {
  title: string; href: string; icon: string; desc: string;
}) {
  return (
    <a
      href={href}
      className="block p-5 rounded-xl border border-gray-700 bg-gray-900 hover:border-blue-500 hover:bg-gray-800 transition-all"
    >
      <div className="text-3xl mb-3">{icon}</div>
      <h2 className="font-semibold text-white">{title}</h2>
      <p className="text-sm text-gray-400 mt-1">{desc}</p>
    </a>
  );
}
