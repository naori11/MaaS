import type { FormEvent, ReactNode } from "react";
import Link from "next/link";

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
        <nav className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 md:px-8">
          <Link href="/login" className="text-2xl font-bold tracking-tight">
            MaaS
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            <Link href="/calculator/focused" className="text-sm font-medium text-[#4d5d73] hover:text-[#b60055]">
              Calculator
            </Link>
            <Link href="/history" className="text-sm font-medium text-[#4d5d73] hover:text-[#b60055]">
              History
            </Link>
            <Link href="/billing" className="text-sm font-medium text-[#4d5d73] hover:text-[#b60055]">
              Billing
            </Link>
          </div>
          <Link href="/signup" className="rounded-xl px-6 py-2 font-semibold text-[#b60055] hover:opacity-80">
            Get Started
          </Link>
        </nav>
      </header>

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-12">
        <div className="pointer-events-none absolute -right-8 -top-14 h-80 w-80 rounded-full bg-[#dce9ff] opacity-70 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-14 -left-8 h-72 w-72 rounded-full bg-[#ffc69c] opacity-25 blur-3xl" />

        <section className="relative z-10 w-full max-w-[480px]">
          <div className="rounded-2xl border border-[#9eaec7]/15 bg-white p-10 shadow-[0px_20px_40px_rgba(32,48,68,0.06)] md:p-12">
            <div className="mb-10 text-center md:text-left">
              <h1 className="text-4xl font-extrabold tracking-tight">{title}</h1>
              <p className="mt-4 text-[#4d5d73]">{subtitle}</p>
            </div>

            <form className="space-y-6" onSubmit={onSubmit} noValidate>
              {children}

              {formError ? (
                <p className="rounded-lg border border-[#fb5151]/20 bg-[#fb5151]/10 px-3 py-2 text-xs font-semibold text-[#b31b25]" role="alert">
                  {formError}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={isSubmitting}
                className="maas-enterprise-gradient w-full rounded-xl py-4 font-bold tracking-wide text-white shadow-lg shadow-[#b60055]/20 transition hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? "Processing..." : actionLabel}
              </button>
            </form>

            <div className="mt-10 border-t border-[#9eaec7]/15 pt-8 text-center">
              <p className="text-sm text-[#4d5d73]">
                {footerPrompt}
                <Link className="ml-1 font-bold text-[#b60055] hover:underline" href={footerHref}>
                  {footerLinkLabel}
                </Link>
              </p>
            </div>
          </div>

          <div className="mt-8 flex items-center justify-between px-3 text-[10px] font-bold uppercase tracking-[0.1em] text-[#4d5d73] opacity-70">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">lock</span>
              Encryption: AES-256
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">terminal</span>
              Status: Online
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[#9eaec7]/15 bg-[#f4f6ff] py-10">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-4 px-6 text-xs uppercase tracking-[0.08em] text-[#4d5d73] md:flex-row md:px-8">
          <div>© 2024 MaaS - The Algorithmic Atelier</div>
          <div className="flex gap-8">
            <Link href="/login" className="hover:text-[#b60055]">
              Login
            </Link>
            <Link href="/signup" className="hover:text-[#b60055]">
              Sign Up
            </Link>
            <Link href="/billing" className="hover:text-[#b60055]">
              Billing
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
