"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { DashboardShell } from "./dashboard-shell";

type AppRouteShellProps = {
  children: ReactNode;
};

const DASHBOARD_ROUTE_META = {
  "/calculator/focused": {
    activeTab: "calculator" as const,
    title: "Calculator View",
    subtitle: "Focused execution mode for high-precision arithmetic operations.",
  },
  "/history": {
    activeTab: "history" as const,
    title: "Calculation History",
    subtitle: "A detailed audit trail of all mathematical operations processed by the MaaS engine.",
  },
  "/billing": {
    activeTab: "billing" as const,
    title: "Scale your logic",
    subtitle: "Transparent pricing designed for everyone from hobbyist calculators to enterprise-grade arithmetic clusters.",
  },
};

export function AppRouteShell({ children }: AppRouteShellProps) {
  const pathname = usePathname();
  const dashboardRoute = DASHBOARD_ROUTE_META[pathname as keyof typeof DASHBOARD_ROUTE_META];

  if (!dashboardRoute) {
    return children;
  }

  return (
    <DashboardShell activeTab={dashboardRoute.activeTab} title={dashboardRoute.title} subtitle={dashboardRoute.subtitle}>
      {children}
    </DashboardShell>
  );
}
