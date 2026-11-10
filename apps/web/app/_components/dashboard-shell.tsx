"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { MotionButton, MotionCard } from "./motion/motion-primitives";
import { RouteContentTransition } from "./motion/route-content-transition";
import { DASHBOARD_TABS, type DashboardTab } from "../_lib/dashboard-nav";
import { LogoutButton } from "./logout-button";
import { getBillingStatus, type BillingStatus } from "../_lib/api/billing";

type DashboardShellProps = {
  activeTab: DashboardTab;
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function DashboardShell({ activeTab, title, subtitle, children }: DashboardShellProps) {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [billingUnavailable, setBillingUnavailable] = useState(false);

  useEffect(() => {
    let mounted = true;
    const refreshBilling = async () => {
      try {
        const data = await getBillingStatus();
        if (mounted) {
          setBilling(data);
          setBillingUnavailable(false);
        }
      } catch {
        if (mounted) {
          setBilling(null);
          setBillingUnavailable(true);
        }
      }
    };

    const onUsageUpdated = () => void refreshBilling();
    void refreshBilling();
    window.addEventListener("maas:usage-updated", onUsageUpdated);
    window.addEventListener("focus", onUsageUpdated);

    return () => {
      mounted = false;
      window.removeEventListener("maas:usage-updated", onUsageUpdated);
      window.removeEventListener("focus", onUsageUpdated);
    };
  }, []);

  const used = billing?.usage?.used ?? 0;
  const isUnlimited = billing?.usage?.unlimited ?? false;
  const isTrial = Boolean(billing?.trial?.is_active);
  const trialDays = billing?.trial?.days_remaining;
  const limitPercent = isUnlimited ? 100 : Math.min(100, Math.round((used / 50) * 100));

  return (
    <div className="flex min-h-dvh flex-col bg-[#f4f6ff] text-[#203044]">
      <header className="sticky top-0 z-40 border-b border-[#9eaec7]/20 bg-[#f4f6ff]/95 backdrop-blur">
        <div className="maas-shell-gutter flex min-h-[var(--maas-header-height)] items-center justify-between gap-3 py-3">
          <div className="flex items-center gap-3">
            <span className="text-xl font-extrabold tracking-tight sm:text-2xl">MaaS</span>
            {isTrial ? (
              <span className="rounded-full bg-[#b60055]/10 px-2.5 py-0.5 text-[11px] font-bold text-[#b60055]">
                Pro Preview: {trialDays}d left
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            <MotionButton className="maas-touch-target rounded-full p-2 hover:bg-[#dce9ff]" ariaLabel="Toggle theme">
              <span className="material-symbols-outlined">light_mode</span>
            </MotionButton>
            <MotionButton className="maas-touch-target relative rounded-full p-2 hover:bg-[#dce9ff]" ariaLabel="Notifications">
              <span className="material-symbols-outlined">notifications</span>
              {isTrial && trialDays && trialDays <= 2 ? (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#b60055]" />
              ) : null}
            </MotionButton>
            <div className="ml-1 h-9 w-9 rounded-full bg-[#c9deff]" aria-hidden="true" />
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="maas-scrollbar sticky top-[var(--maas-header-height)] hidden max-h-[calc(100svh-var(--maas-header-height))] w-full max-w-[clamp(13rem,20vw,18rem)] overflow-y-auto border-r border-[#9eaec7]/20 bg-[#f4f6ff] px-4 py-6 md:flex md:flex-col md:px-5 lg:px-6">
          <div className="mb-6">
            <h2 className="text-xl font-black">MaaS</h2>
            <p className="text-[10px] uppercase tracking-[0.2em] text-[#4d5d73]">Math as a Service</p>
          </div>
          <nav className="flex flex-col gap-2" aria-label="Dashboard navigation">
            {DASHBOARD_TABS.map((tab) => (
              <MotionCard key={`side-card-${tab.key}`}>
                <Link
                  key={`side-${tab.key}`}
                  href={tab.href}
                  aria-current={activeTab === tab.key ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-bold uppercase tracking-[0.15em] transition lg:px-4 lg:py-3 ${
                    activeTab === tab.key
                      ? "translate-x-1 border-r-4 border-[#b60055] bg-[#eaf1ff] text-[#b60055]"
                      : "text-[#4d5d73] hover:bg-[#dce9ff]"
                  }`}
                >
                  <span
                    className="material-symbols-outlined"
                    style={activeTab === tab.key ? { fontVariationSettings: "'FILL' 1" } : undefined}
                  >
                    {tab.icon}
                  </span>
                  {tab.label}
                </Link>
              </MotionCard>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl bg-[#dce9ff]/60 p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#4d5d73]">Daily Usage</p>
              <span className="text-[10px] font-medium text-[#4d5d73]">Reset 00:00 UTC</span>
            </div>
            {billingUnavailable ? (
              <p className="text-xs font-semibold text-[#8b3a4a]">Usage unavailable. Retry by refreshing.</p>
            ) : billing === null ? (
              <p className="text-xs font-semibold text-[#4d5d73]">Loading usage…</p>
            ) : isUnlimited ? (
              <p className="text-xs font-semibold text-[#203044]">
                Unlimited {isTrial ? "(Pro Preview)" : "(Pro Plan)"}
              </p>
            ) : (
              <>
                <div className="mb-2 h-1 w-full rounded-full bg-[#c9deff]">
                  <div className="h-full rounded-full bg-[#b60055] transition-all" style={{ width: `${limitPercent}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span>{used} / {billing.usage?.limit ?? 50} calcs</span>
                  {used >= (billing.usage?.limit ?? 50) ? (
                    <Link href="/billing" className="text-[#b60055] hover:underline">Upgrade</Link>
                  ) : null}
                </div>
              </>
            )}
          </div>
        </aside>

        <main className="maas-scrollbar maas-shell-gutter maas-mobile-nav-safe w-full flex-1 overflow-y-auto pt-8 md:px-8 md:py-10 md:pb-10 lg:px-10 lg:py-12">
          <section className="mb-6 rounded-2xl bg-[#dce9ff]/60 p-4 md:hidden" aria-live="polite" aria-label="Daily calculation usage">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#4d5d73]">Daily Usage</p>
              <span className="text-[10px] font-medium text-[#4d5d73]">Reset 00:00 UTC</span>
            </div>
            {billingUnavailable ? (
              <p className="text-xs font-semibold text-[#8b3a4a]">Usage unavailable. Refresh to retry.</p>
            ) : billing === null ? (
              <p className="text-xs font-semibold text-[#4d5d73]">Loading usage…</p>
            ) : isUnlimited ? (
              <p className="text-xs font-semibold text-[#203044]">Unlimited {isTrial ? "(Pro Preview)" : "(Pro Plan)"}</p>
            ) : (
              <>
                <div className="mb-2 h-1 w-full rounded-full bg-[#c9deff]">
                  <div className="h-full rounded-full bg-[#b60055] transition-all" style={{ width: `${limitPercent}%` }} />
                </div>
                <p className="text-xs font-semibold">{used} / {billing.usage?.limit ?? 50} calculations</p>
              </>
            )}
          </section>
          <RouteContentTransition>
            <div className="mb-8 md:mb-10">
              <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl">{title}</h1>
              {subtitle ? <p className="mt-3 max-w-3xl text-sm text-[#4d5d73] sm:text-base">{subtitle}</p> : null}
            </div>
            {children}
          </RouteContentTransition>
        </main>
      </div>

      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-[#9eaec7]/20 bg-[#eaf1ff]/95 px-2 pt-2 backdrop-blur maas-mobile-nav-inset md:hidden"
        aria-label="Mobile dashboard navigation"
      >
        {DASHBOARD_TABS.map((tab) => (
          <MotionCard key={`mobile-card-${tab.key}`}>
            <Link
              key={`mobile-${tab.key}`}
              href={tab.href}
              aria-current={activeTab === tab.key ? "page" : undefined}
              className="flex min-h-11 min-w-16 flex-col items-center justify-center gap-1 rounded-lg px-2"
            >
              <span
                className={`material-symbols-outlined ${activeTab === tab.key ? "text-[#b60055]" : "text-[#4d5d73]"}`}
                style={activeTab === tab.key ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {tab.icon}
              </span>
              <span className={`text-[10px] font-bold uppercase ${activeTab === tab.key ? "text-[#b60055]" : "text-[#4d5d73]"}`}>
                {tab.short}
              </span>
            </Link>
          </MotionCard>
        ))}
      </nav>
    </div>
  );
}
