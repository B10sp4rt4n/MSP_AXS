import type { ReactNode } from "react";
import PortalRoleGate from "@/components/PortalRoleGate";
import { PORTAL_ROLES } from "@/lib/portal-roles";

export default function MSPLayout({ children }: { children: ReactNode }) {
  return <PortalRoleGate roles={PORTAL_ROLES.msp}>{children}</PortalRoleGate>;
}
