import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { readAuthTokenFromCookieStore } from "./_lib/auth/cookies";

export default async function Home() {
  const cookieStore = await cookies();
  const isAuthenticated = Boolean(readAuthTokenFromCookieStore(cookieStore));

  redirect(isAuthenticated ? "/calculator/focused" : "/login");
}
