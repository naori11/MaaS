import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { MOCK_AUTH_COOKIE } from "./_lib/mock-auth";

export default async function Home() {
  const cookieStore = await cookies();
  const isAuthenticated = Boolean(cookieStore.get(MOCK_AUTH_COOKIE)?.value);

  redirect(isAuthenticated ? "/calculator/focused" : "/login");
}
