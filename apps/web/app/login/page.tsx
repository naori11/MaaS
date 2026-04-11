"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { AuthShell } from "../_components/auth-shell";
import { resolvePostAuthRedirect, setMockAuthCookie } from "../_lib/mock-auth";

function LoginPageContent() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const nextPath = useMemo(() => resolvePostAuthRedirect(searchParams.get("next")), [searchParams]);

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current !== null) {
        clearTimeout(redirectTimerRef.current);
      }
    };
  }, []);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      setError("Node Identity and Access Cipher are required.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    redirectTimerRef.current = setTimeout(() => {
      setMockAuthCookie();
      router.push(nextPath);
      router.refresh();
    }, 250);
  };

  return (
    <AuthShell
      title="Initiate Session"
      subtitle="Enterprise-grade security for your addition. Sign in to compute."
      actionLabel="Initiate Session"
      footerPrompt="New computational node?"
      footerLinkLabel="Request Partition (Sign Up)"
      footerHref="/signup"
      formError={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    >
      <div className="space-y-2">
        <label htmlFor="email" className="ml-1 text-xs font-bold uppercase tracking-[0.05em] text-[#4d5d73]">
          Node Identity
        </label>
        <div className="group relative">
          <div className="pointer-events-none absolute inset-y-0 left-4 flex items-center text-[#68788f]">
            <span className="material-symbols-outlined text-[20px]">alternate_email</span>
          </div>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="identifier@network.maas"
            className="w-full rounded-lg border border-[#9eaec7]/20 bg-white py-4 pl-12 pr-4 text-[#203044] outline-none transition placeholder:text-[#68788f]/60 focus:border-[#b60055] focus:ring-2 focus:ring-[#b60055]/10"
          />
        </div>
      </div>

      <div className="space-y-2">
        <div className="ml-1 flex items-center justify-between">
          <label htmlFor="password" className="text-xs font-bold uppercase tracking-[0.05em] text-[#4d5d73]">
            Access Cipher
          </label>
          <Link href="/signup" className="text-[10px] font-bold uppercase tracking-[0.05em] text-[#b60055] hover:opacity-80">
            Forgot Cipher?
          </Link>
        </div>
        <div className="group relative">
          <div className="pointer-events-none absolute inset-y-0 left-4 flex items-center text-[#68788f]">
            <span className="material-symbols-outlined text-[20px]">lock</span>
          </div>
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••••••"
            className="w-full rounded-lg border border-[#9eaec7]/20 bg-white py-4 pl-12 pr-12 text-[#203044] outline-none transition placeholder:text-[#68788f]/60 focus:border-[#b60055] focus:ring-2 focus:ring-[#b60055]/10"
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label="Toggle password visibility"
            aria-pressed={showPassword}
            className="absolute inset-y-0 right-4 flex items-center text-[#68788f] hover:text-[#203044]"
          >
            <span className="material-symbols-outlined text-[20px]">
              {showPassword ? "visibility_off" : "visibility"}
            </span>
          </button>
        </div>
      </div>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageContent />
    </Suspense>
  );
}
