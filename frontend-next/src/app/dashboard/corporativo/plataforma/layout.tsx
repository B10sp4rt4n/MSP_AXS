import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { api } from "@/lib/api";

export default async function CorporatePlatformLayout({ children }: { children: ReactNode }) {
  const { userId, getToken } = await auth();
  if (!userId) redirect("/sign-in");
  try {
    const token = await getToken();
    if (!token) throw new Error("Sin sesión");
    // La autoridad GLOBAL viene del backend AUP_GOV, no del rol del cliente.
    const state = await api.get<{ autorizado: boolean }>("/plataforma/corporativo/estado", token);
    if (state.autorizado === true) return <>{children}</>;
  } catch {
    // Fallo cerrado. Sin flag, GOV o backend disponible no se montan formularios.
  }
  return <main className="min-h-screen bg-gray-950 p-6 text-white">
    <h1 className="text-xl font-semibold">AXS Corporativo · Superadmin</h1>
    <p role="alert" className="mt-4 text-gray-300">
      No se puede habilitar la consola. Requiere autoridad GLOBAL y aprovisionamiento autorizado por el backend.
    </p>
    <a href="/dashboard" className="mt-5 inline-block text-blue-300 underline">Volver al inicio</a>
  </main>;
}
