import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import MSPClient from "./MSPClient";

export default async function MSPPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <MSPClient />;
}
