"use client";

import { useEffect, useState } from "react";
import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import { api } from "@/lib/api";
import { PORTAL_ROLES } from "@/lib/portal-roles";

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
  roles: readonly string[];
}[] = [
  {
    title: "Portal Guardia",
    href: "/dashboard/guardia",
    icon: "🛡️",
    desc: "Registrar entradas, salidas y validar QR",
    roles: PORTAL_ROLES.guardia,
  },
  {
    title: "Portal Residente",
    href: "/dashboard/residente",
    icon: "🏠",
    desc: "Preregistrar visitas y generar QR de acceso",
    roles: PORTAL_ROLES.residente,
  },
  {
    title: "Panel Admin",
    href: "/dashboard/admin",
    icon: "⚙️",
    desc: "Visitas, casas y usuarios del condominio",
    roles: PORTAL_ROLES.admin,
  },
  {
    title: "Dashboard MSP",
    href: "/dashboard/msp",
    icon: "🏢",
    desc: "Vista global de condominios y usuarios del sistema",
    roles: PORTAL_ROLES.msp,
  },
];

export default function DashboardClient() {
  const { user } = useUser();
  const { getToken, userId, isLoaded } = useAuth();
  const [profile, setProfile] = useState<{ userId: string; data: MeResponse } | null>(null);
  const [failure, setFailure] = useState<{ userId: string; message: string } | null>(null);
  const me = profile && profile.userId === userId ? profile.data : null;
  const error = failure && failure.userId === userId ? failure.message : "";

  useEffect(() => {
    if (!isLoaded || !userId) return;
    let active = true;
    getToken()
      .then((token) => {
        if (!token) throw new Error("Sin sesión");
        return api.get<MeResponse>("/auth/me", token);
      })
      .then((data) => {
        if (active) { setProfile({ userId, data }); setFailure(null); }
      })
      .catch(() => {
        if (active) {
          setProfile(null);
          setFailure({ userId, message: "No pudimos comprobar tus permisos. Intenta de nuevo." });
        }
      });
    return () => { active = false; };
  }, [getToken, userId, isLoaded]);

  const portales = me
    ? PORTALES.filter((p) => p.roles.includes(me.rol))
    : [];

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
        {!me && !error && <p role="status" className="text-gray-400">Comprobando permisos...</p>}
        {error && <div role="alert" className="text-red-400">
          <p>{error}</p>
          <a href="/dashboard" className="text-blue-400">Reintentar</a>
        </div>}
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
