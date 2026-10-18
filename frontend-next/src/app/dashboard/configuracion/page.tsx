import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import AxsBrand from "@/components/AxsBrand";
import IdentityProfile from "@/components/IdentityProfile";

export default async function ConfiguracionPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <AxsBrand />
        <a href="/dashboard" className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-blue-400">
          Volver a operación
        </a>
      </header>
      <main className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-semibold">Configuración</h1>
        <p className="mt-2 text-sm text-gray-400">Administra tu identidad y tus datos personales.</p>
        <IdentityProfile key={userId} />
      </main>
    </div>
  );
}
