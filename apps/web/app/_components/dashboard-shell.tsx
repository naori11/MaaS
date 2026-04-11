"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { MotionButton, MotionCard } from "./motion/motion-primitives";
import { RouteContentTransition } from "./motion/route-content-transition";
import { DASHBOARD_TABS, type DashboardTab } from "../_lib/dashboard-nav";
import { LogoutButton } from "./logout-button";

type DashboardShellProps = {
  activeTab: DashboardTab;
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function DashboardShell({ activeTab, title, subtitle, children }: DashboardShellProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-[#f4f6ff] text-[#203044]">
      <header className="sticky top-0 z-40 border-b border-[#9eaec7]/20 bg-[#f4f6ff]/95 backdrop-blur">
        <div className="maas-shell-gutter flex min-h-[var(--maas-header-height)] items-center justify-between gap-3 py-3">
          <span className="text-xl font-extrabold tracking-tight sm:text-2xl">MaaS</span>
          <div className="flex items-center gap-1.5 sm:gap-2">
            <MotionButton className="maas-touch-target rounded-full p-2 hover:bg-[#dce9ff]" ariaLabel="Toggle theme">
              <span className="material-symbols-outlined">light_mode</span>
            </MotionButton>
            <MotionButton className="maas-touch-target relative rounded-full p-2 hover:bg-[#dce9ff]" ariaLabel="Notifications">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#b60055]" />
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
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#4d5d73]">Current Usage</p>
            <div className="mb-2 h-1 w-full rounded-full bg-[#c9deff]">
              <div className="h-full w-2/3 rounded-full bg-[#b60055]" />
            </div>
            <p className="text-xs font-semibold">66% of Pro Limit</p>
          </div>
        </aside>

        <main className="maas-scrollbar maas-shell-gutter maas-mobile-nav-safe w-full flex-1 overflow-y-auto pt-8 md:px-8 md:py-10 md:pb-10 lg:px-10 lg:py-12">
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
