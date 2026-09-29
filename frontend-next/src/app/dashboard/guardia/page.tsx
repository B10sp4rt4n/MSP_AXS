import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import GuardiaClient from "./GuardiaClient";

export default async function GuardiaPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <GuardiaClient />;
}
