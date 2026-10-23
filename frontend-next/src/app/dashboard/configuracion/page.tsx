import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import AxsBrand from "@/components/AxsBrand";
import IdentityProfile from "@/components/IdentityProfile";
import Link from "next/link";
import { ARCO_PATH } from "@/lib/privacidad";

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
        <section className="mt-8 rounded-xl border border-gray-800 p-5">
          <h2 className="text-lg font-semibold">Privacidad y derechos ARCO</h2>
          <p className="mt-2 text-sm text-gray-400">Conoce cómo solicitar acceso, corrección, cancelación u oposición al tratamiento de tus datos personales.</p>
          <Link href={ARCO_PATH} className="mt-3 inline-flex min-h-11 items-center text-purple-300 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-purple-400">
            Consultar mis derechos y el canal de atención
          </Link>
        </section>
      </main>
    </div>
  );
}
