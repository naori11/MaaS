export type DashboardTab = "calculator" | "history" | "billing";

export type DashboardNavItem = {
  key: DashboardTab;
  label: string;
  short: string;
  href: string;
  icon: string;
};

export const DASHBOARD_TABS: DashboardNavItem[] = [
  { key: "calculator", label: "Calculator", short: "Calc", href: "/calculator/focused", icon: "calculate" },
  { key: "history", label: "History", short: "History", href: "/history", icon: "history" },
  { key: "billing", label: "Billing", short: "Billing", href: "/billing", icon: "payments" },
];
