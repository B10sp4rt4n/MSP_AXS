import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { api } from "@/lib/api";

export default async function PortalRoleGate({ roles, children }: {
  roles: readonly string[];
  children: ReactNode;
}) {
  const { userId, getToken } = await auth();
  if (!userId) redirect("/sign-in");

  let role: string;
  try {
    const token = await getToken();
    if (!token) throw new Error("Sin sesión");
    const me = await api.get<{ rol: string }>("/auth/me", token);
    role = me.rol;
  } catch {
    return <PortalNotice message="No pudimos comprobar tus permisos. Vuelve al inicio e intenta de nuevo." />;
  }

  if (!roles.includes(role)) {
    return <PortalNotice message="Tu cuenta no tiene permiso para usar este portal. En el inicio encontrarás las opciones de tu rol." />;
  }
  return children;
}

function PortalNotice({ message }: { message: string }) {
  return <main className="min-h-screen bg-gray-950 text-white p-6">
    <h1 className="text-xl font-bold mb-3">Acceso al portal</h1>
    <p role="alert" className="text-gray-300 mb-4">{message}</p>
    <a href="/dashboard" className="text-blue-400">Volver al inicio</a>
  </main>;
}
