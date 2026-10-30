import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_EXPIRES_AT_COOKIE, readAuthTokenFromCookieStore } from "./_lib/auth/cookies";

export default async function Home() {
  const cookieStore = await cookies();
  const token = readAuthTokenFromCookieStore(cookieStore);
  const expiresAtRaw = cookieStore.get(AUTH_EXPIRES_AT_COOKIE)?.value;
  const expiresAt = Number(expiresAtRaw);
  const isExpired = Number.isFinite(expiresAt) && Date.now() >= expiresAt;
  const isAuthenticated = Boolean(token) && !isExpired;

  redirect(isAuthenticated ? "/calculator/focused" : "/login");
}
