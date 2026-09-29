import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import ResidenteClient from "./ResidenteClient";

export default async function ResidentePage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <ResidenteClient />;
}
