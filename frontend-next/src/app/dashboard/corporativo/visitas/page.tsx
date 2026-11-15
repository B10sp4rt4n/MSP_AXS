import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import CorporateVisitsClient from "./CorporateVisitsClient";

export default async function Page({ searchParams }: {
  searchParams: Promise<{ empresa?: string; sede?: string }>;
}) {
  const query = await searchParams;
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <CorporateVisitsClient tenant={typeof query.empresa === "string" ? query.empresa : ""}
    site={typeof query.sede === "string" ? query.sede : ""} />;
}
