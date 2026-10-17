import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import NuevaVisitaClient from "./NuevaVisitaClient";

export default async function NuevaVisitaPage({ searchParams }: { searchParams: Promise<{ destino?: string; condominio?: string }> }) {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  const params = await searchParams;
  return <NuevaVisitaClient initialDestino={typeof params.destino === "string" ? params.destino : ""} initialCondominio={typeof params.condominio === "string" ? params.condominio : ""} />;
}
