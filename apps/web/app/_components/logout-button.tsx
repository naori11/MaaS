"use client";

import { clearMockAuthCookie } from "../_lib/mock-auth";

export function LogoutButton() {
  const handleLogout = () => {
    clearMockAuthCookie();
    window.location.assign("/login");
  };

  return (
    <button
      type="button"
      onClick={handleLogout}
      className="rounded-lg border border-[#9eaec7]/25 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.08em] text-[#4d5d73] transition hover:bg-[#dce9ff]"
    >
      Sign out
    </button>
  );
}
