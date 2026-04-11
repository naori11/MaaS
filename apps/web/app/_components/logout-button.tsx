"use client";

import { MotionButton } from "./motion/motion-primitives";
import { clearAuthSession } from "../_lib/auth/session";

export function LogoutButton() {
  const handleLogout = () => {
    clearAuthSession();
    window.location.assign("/login");
  };

  return (
    <MotionButton
      type="button"
      onClick={handleLogout}
      className="rounded-lg border border-[#9eaec7]/25 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.08em] text-[#4d5d73] transition hover:bg-[#dce9ff]"
    >
      Sign out
    </MotionButton>
  );
}
