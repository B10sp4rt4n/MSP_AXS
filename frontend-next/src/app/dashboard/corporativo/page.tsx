import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import CorporateDirectoryClient from "./CorporateDirectoryClient";

export default async function CorporateDirectoryPage({ searchParams }: {
  searchParams: Promise<{ empresa?: string | string[] }>;
}) {
  const query = await searchParams;
  const tenant = typeof query.empresa === "string" ? query.empresa : "";
  const returnPath = `/dashboard/corporativo${tenant ? `?empresa=${encodeURIComponent(tenant)}` : ""}`;
  const { userId } = await auth();
  if (!userId) redirect(`/sign-in?redirect_url=${encodeURIComponent(returnPath)}`);
  return <CorporateDirectoryClient initialTenant={tenant} />;
}
