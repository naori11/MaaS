"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MotionSection } from "../_components/motion/motion-primitives";
import { AuthShell } from "../_components/auth-shell";
import { resolvePostAuthRedirect, setAuthSession } from "../_lib/mock-auth";

function SignupPageContent() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();
  const searchParams = useSearchParams();

  const nextPath = useMemo(() => resolvePostAuthRedirect(searchParams.get("next")), [searchParams]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      setError("Node Identity and Access Cipher are required.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const gatewayBaseUrl = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:4000").replace(/\/$/, "");

      const registerResponse = await fetch(`${gatewayBaseUrl}/api/v1/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const registerPayload = (await registerResponse.json()) as { error?: { message?: string } } | undefined;

      if (!registerResponse.ok) {
        setError(registerPayload?.error?.message ?? "Unable to create account.");
        return;
      }

      const loginResponse = await fetch(`${gatewayBaseUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const loginPayload = (await loginResponse.json()) as
        | { access_token?: string; token_type?: string; expires_in?: number; error?: { message?: string } }
        | undefined;

      if (!loginResponse.ok || !loginPayload?.access_token) {
        setError(loginPayload?.error?.message ?? "Account created. Please sign in.");
        router.push(`/login?next=${encodeURIComponent(nextPath)}`);
        router.refresh();
        return;
      }

      setAuthSession({
        accessToken: loginPayload.access_token,
        tokenType: loginPayload.token_type ?? "bearer",
        expiresInSeconds: loginPayload.expires_in ?? 3600,
      });

      router.push(nextPath);
      router.refresh();
    } catch {
      setError("Unable to reach authentication gateway.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Provision Account"
      subtitle="Start your journey into high-performance arithmetic. Provision your account."
      actionLabel="Provision Account"
      footerPrompt="Already have a partition?"
      footerLinkLabel="Sign in"
      footerHref="/login"
      formError={error}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmit}
    >
      <MotionSection>
        <div className="space-y-2">
          <label htmlFor="signup-name" className="ml-1 text-[10px] font-bold uppercase tracking-[0.05em] text-[#4d5d73]">
            Full Name
          </label>
          <input
            id="signup-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Leonhard Euler"
            className="w-full rounded-lg border border-[#9eaec7]/20 bg-white px-4 py-4 text-[#203044] outline-none transition placeholder:text-[#68788f] focus:border-[#b60055] focus:ring-2 focus:ring-[#b60055]/10"
          />
        </div>
      </MotionSection>

      <MotionSection>
        <div className="space-y-2">
          <label htmlFor="signup-email" className="ml-1 text-[10px] font-bold uppercase tracking-[0.05em] text-[#4d5d73]">
            Node Identity
          </label>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="euler@algorithmic.atelier"
            className="w-full rounded-lg border border-[#9eaec7]/20 bg-white px-4 py-4 text-[#203044] outline-none transition placeholder:text-[#68788f] focus:border-[#b60055] focus:ring-2 focus:ring-[#b60055]/10"
          />
        </div>
      </MotionSection>

      <MotionSection>
        <div className="space-y-2">
          <label htmlFor="signup-password" className="ml-1 text-[10px] font-bold uppercase tracking-[0.05em] text-[#4d5d73]">
            Access Cipher
          </label>
          <input
            id="signup-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••••••"
            className="w-full rounded-lg border border-[#9eaec7]/20 bg-white px-4 py-4 text-[#203044] outline-none transition placeholder:text-[#68788f] focus:border-[#b60055] focus:ring-2 focus:ring-[#b60055]/10"
          />
        </div>
      </MotionSection>
    </AuthShell>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={null}>
      <SignupPageContent />
    </Suspense>
  );
}
