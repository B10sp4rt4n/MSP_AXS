import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import ValidarQRClient from "./ValidarQRClient";

export default async function ValidarQRPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <ValidarQRClient />;
}
