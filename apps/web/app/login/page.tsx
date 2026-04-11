"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { MotionSection } from "../_components/motion/motion-primitives";
import { AuthShell } from "../_components/auth-shell";
import { resolvePostAuthRedirect } from "../_lib/mock-auth";
import { loginWithPassword } from "../_lib/api/auth-login";
import { setAuthSession } from "../_lib/auth/session";

function LoginPageContent() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();
  const searchParams = useSearchParams();

  const nextPath = useMemo(() => resolvePostAuthRedirect(searchParams.get("next")), [searchParams]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError("Node Identity and Access Cipher are required.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const response = await loginWithPassword({
        email: trimmedEmail,
        password: trimmedPassword,
      });

      setAuthSession({
        accessToken: response.access_token,
        tokenType: response.token_type,
        expiresInSeconds: response.expires_in,
      });

      router.push(nextPath);
      router.refresh();
    } catch (submitError) {
      const message = submitError instanceof Error && submitError.message.trim() ? submitError.message : "Unable to initiate session.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
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
      <MotionSection>
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
      </MotionSection>

      <MotionSection>
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
      </MotionSection>
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
