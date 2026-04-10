"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthShell } from "../_components/auth-shell";
import { resolvePostAuthRedirect, setMockAuthCookie } from "../_lib/mock-auth";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();
  const searchParams = useSearchParams();

  const nextPath = useMemo(() => resolvePostAuthRedirect(searchParams.get("next")), [searchParams]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!name.trim() || !email.trim() || !password.trim()) {
      setError("Full Name, Node Identity, and Access Cipher are required.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    setTimeout(() => {
      setMockAuthCookie();
      router.push(nextPath);
      router.refresh();
    }, 250);
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
    </AuthShell>
  );
}
