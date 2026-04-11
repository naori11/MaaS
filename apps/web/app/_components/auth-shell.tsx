"use client";

import type { FormEvent, ReactNode } from "react";
import Link from "next/link";
import { MotionButton, MotionSection } from "./motion/motion-primitives";

type AuthShellProps = {
  title: string;
  subtitle: string;
  actionLabel: string;
  footerPrompt: string;
  footerLinkLabel: string;
  footerHref: string;
  formError?: string;
  isSubmitting?: boolean;
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
};

export function AuthShell({
  title,
  subtitle,
  actionLabel,
  footerPrompt,
  footerLinkLabel,
  footerHref,
  formError,
  isSubmitting,
  onSubmit,
  children,
}: AuthShellProps) {
  return (
    <div className="relative flex min-h-screen flex-col bg-[#f4f6ff] text-[#203044]">
      <header className="sticky top-0 z-30 border-b border-[#9eaec7]/20 bg-[#f4f6ff]/95 backdrop-blur">
        <nav className="maas-shell-gutter mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-3 py-4" aria-label="Primary">
          <Link href="/login" className="text-2xl font-bold tracking-tight">
            MaaS
          </Link>
          <div className="order-3 flex w-full items-center justify-center gap-2 rounded-xl bg-[#eaf1ff] p-2 sm:gap-3 md:order-2 md:w-auto md:bg-transparent md:p-0">
            <Link href="/calculator/focused" className="maas-touch-target inline-flex items-center rounded-lg px-3 text-xs font-semibold text-[#4d5d73] hover:text-[#b60055] md:text-sm">
              Calculator
            </Link>
            <Link href="/history" className="maas-touch-target inline-flex items-center rounded-lg px-3 text-xs font-semibold text-[#4d5d73] hover:text-[#b60055] md:text-sm">
              History
            </Link>
            <Link href="/billing" className="maas-touch-target inline-flex items-center rounded-lg px-3 text-xs font-semibold text-[#4d5d73] hover:text-[#b60055] md:text-sm">
              Billing
            </Link>
          </div>
          <Link href="/signup" className="maas-touch-target order-2 inline-flex items-center rounded-xl px-4 py-2 text-sm font-semibold text-[#b60055] hover:opacity-80 md:order-3 md:px-6">
            Get Started
          </Link>
        </nav>
      </header>

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-8 sm:px-6 sm:py-10 md:px-8 md:py-12">
        <div className="pointer-events-none absolute -right-8 -top-14 h-[45vw] max-h-80 min-h-56 w-[45vw] max-w-80 min-w-56 rounded-full bg-[#dce9ff] opacity-70 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-14 -left-8 h-[42vw] max-h-72 min-h-52 w-[42vw] max-w-72 min-w-52 rounded-full bg-[#ffc69c] opacity-25 blur-3xl" />

        <MotionSection className="relative z-10 w-full max-w-[min(100%,30rem)]">
          <div className="rounded-2xl border border-[#9eaec7]/15 bg-white p-6 shadow-[0px_20px_40px_rgba(32,48,68,0.06)] sm:p-8 md:p-10">
            <div className="mb-8 text-center md:mb-10 md:text-left">
              <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
              <p className="mt-3 text-sm text-[#4d5d73] sm:mt-4 sm:text-base">{subtitle}</p>
            </div>

            <form className="space-y-5 sm:space-y-6" onSubmit={onSubmit} noValidate>
              {children}

              {formError ? (
                <p className="rounded-lg border border-[#fb5151]/20 bg-[#fb5151]/10 px-3 py-2 text-xs font-semibold text-[#b31b25]" role="alert">
                  {formError}
                </p>
              ) : null}

              <MotionButton
                type="submit"
                disabled={isSubmitting}
                className="maas-enterprise-gradient maas-touch-target w-full rounded-xl px-4 py-3 font-bold tracking-wide text-white shadow-lg shadow-[#b60055]/20 transition hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? "Processing..." : actionLabel}
              </MotionButton>
            </form>

            <div className="mt-8 border-t border-[#9eaec7]/15 pt-6 text-center sm:mt-10 sm:pt-8">
              <p className="text-sm text-[#4d5d73]">
                {footerPrompt}
                <Link className="ml-1 font-bold text-[#b60055] hover:underline" href={footerHref}>
                  {footerLinkLabel}
                </Link>
              </p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3 px-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#4d5d73] opacity-70 sm:mt-8 sm:justify-between sm:px-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">lock</span>
              Encryption: AES-256
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">terminal</span>
              Status: Online
            </div>
          </div>
        </MotionSection>
      </main>

      <footer className="border-t border-[#9eaec7]/15 bg-[#f4f6ff] py-8 md:py-10">
        <div className="maas-shell-gutter mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-4 text-center text-xs uppercase tracking-[0.08em] text-[#4d5d73] md:flex-row md:text-left">
          <div>© 2024 MaaS - The Algorithmic Atelier</div>
          <div className="flex flex-wrap items-center justify-center gap-5 sm:gap-8">
            <Link href="/login" className="maas-touch-target inline-flex items-center hover:text-[#b60055]">
              Login
            </Link>
            <Link href="/signup" className="maas-touch-target inline-flex items-center hover:text-[#b60055]">
              Sign Up
            </Link>
            <Link href="/billing" className="maas-touch-target inline-flex items-center hover:text-[#b60055]">
              Billing
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
