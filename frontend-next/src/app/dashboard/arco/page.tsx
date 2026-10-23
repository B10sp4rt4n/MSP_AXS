import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import ArcoClient from "./ArcoClient";

export default async function ArcoPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <ArcoClient />;
}
