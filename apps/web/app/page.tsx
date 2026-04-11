import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_EXPIRES_AT_COOKIE, AUTH_TOKEN_COOKIE } from "./_lib/mock-auth";

export default async function Home() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  const expiresAtRaw = cookieStore.get(AUTH_EXPIRES_AT_COOKIE)?.value;
  const expiresAt = Number(expiresAtRaw);
  const isExpired = Number.isFinite(expiresAt) && Date.now() >= expiresAt;
  const isAuthenticated = Boolean(token) && !isExpired;

  redirect(isAuthenticated ? "/calculator/focused" : "/login");
}
