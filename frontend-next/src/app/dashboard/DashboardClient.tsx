"use client";

import AxsBrand from "@/components/AxsBrand";
import { useEffect, useState } from "react";
import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { PORTAL_ROLES } from "@/lib/portal-roles";
import { forgetCorporateWorkspace, readCorporateWorkspace, verifiedCorporateEntry } from "@/lib/corporate-entry";

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
  const router = useRouter();
  const [revision, setRevision] = useState(0);
  const [profile, setProfile] = useState<{ userId: string; data: MeResponse } | null>(null);
  const [failure, setFailure] = useState<{ userId: string; message: string } | null>(null);
  const me = profile && profile.userId === userId ? profile.data : null;
  const error = failure && failure.userId === userId ? failure.message : "";

  useEffect(() => {
    if (!isLoaded || !userId) return;
    const controller = new AbortController();
    (async () => {
      try {
        const token = await getToken();
        if (controller.signal.aborted) return;
        if (!token) throw new Error("Sin sesión");
        const data = await api.get<MeResponse>("/auth/me", token, controller.signal);
        if (controller.signal.aborted) return;
        const workspace = readCorporateWorkspace(userId);
        if (workspace) {
          const href = await verifiedCorporateEntry(workspace, token, controller.signal);
          if (!controller.signal.aborted) router.replace(href);
          return;
        }
        setProfile({ userId, data }); setFailure(null);
      } catch {
        if (!controller.signal.aborted) {
          setProfile(null);
          setFailure({ userId, message: "No pudimos comprobar tus permisos. Intenta de nuevo o selecciona otro acceso." });
        }
      }
    })();
    return () => controller.abort();
  }, [getToken, userId, isLoaded, router, revision]);

  const portales = me
    ? PORTALES.filter((p) => p.roles.includes(me.rol))
    : [];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex flex-wrap gap-4 items-center justify-between">
        <AxsBrand />
        <div className="flex items-center gap-3">
          <a href="/dashboard/configuracion" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-blue-400">
            Configuración
          </a>
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
          {userId && <button className="ml-4 text-blue-400" onClick={() => {
            forgetCorporateWorkspace(userId); setFailure(null); setProfile(null); setRevision(value => value + 1);
          }}>Usar otro acceso</button>}
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
          {me && <DashCard title="Acceso corporativo" href="/dashboard/corporativo" icon="🏢"
            desc="Abrir la empresa y sede que te compartió tu administrador" />}
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
