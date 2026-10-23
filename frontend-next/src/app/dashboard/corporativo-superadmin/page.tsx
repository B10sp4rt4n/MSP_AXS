import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import CorporativoSuperadminClient from "./CorporativoSuperadminClient";

export default async function CorporativoSuperadminPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <CorporativoSuperadminClient />;
}
