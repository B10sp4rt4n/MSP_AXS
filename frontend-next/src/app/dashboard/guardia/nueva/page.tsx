import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import NuevaVisitaClient from "./NuevaVisitaClient";

export default async function NuevaVisitaPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <NuevaVisitaClient />;
}
