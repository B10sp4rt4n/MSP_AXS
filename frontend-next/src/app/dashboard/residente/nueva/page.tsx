import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import PreregistroClient from "./PreregistroClient";

export default async function PreregistroPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <PreregistroClient />;
}
