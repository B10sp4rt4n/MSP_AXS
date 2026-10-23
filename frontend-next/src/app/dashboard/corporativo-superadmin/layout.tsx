import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { api } from "@/lib/api";

export default async function CorporativoSuperadminLayout({ children }: { children: ReactNode }) {
  const { userId, getToken } = await auth();
  if (!userId) redirect("/sign-in");
  try {
    const token = await getToken();
    if (!token) throw new Error("Sin sesión");
    // GOV GLOBAL se comprueba en el backend; MSP_ADMIN por sí solo no autoriza.
    const access = await api.get<{ authorized: boolean; provisioning_enabled: boolean }>(
      "/plataforma/corporativo/acceso", token);
    if (access.authorized === true && access.provisioning_enabled === true) return <>{children}</>;
  } catch {
    // Falla cerrada si Clerk, GOV, flags o API no están disponibles.
  }
  return <main className="min-h-screen bg-gray-950 p-6 text-white">
    <h1 className="text-xl font-semibold">AXS Corporativo · Superadmin</h1>
    <p role="alert" className="mt-4 text-gray-300">
      Consola no disponible. Se requiere autoridad GLOBAL activa y backend corporativo habilitado.
    </p>
    <a href="/dashboard/msp" className="mt-5 inline-block text-blue-300 underline">Volver al panel MSP</a>
  </main>;
}
