import { NextResponse, type NextRequest } from "next/server";
import { AUTH_EXPIRES_AT_COOKIE, AUTH_TOKEN_COOKIE } from "./app/_lib/mock-auth";

const AUTH_PATHS = new Set(["/login", "/signup"]);

function isProtectedPath(pathname: string) {
  return pathname.startsWith("/calculator") || pathname.startsWith("/history") || pathname.startsWith("/billing");
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(AUTH_TOKEN_COOKIE)?.value;
  const expiresAtRaw = request.cookies.get(AUTH_EXPIRES_AT_COOKIE)?.value;
  const expiresAt = Number(expiresAtRaw);
  const isExpired = Number.isFinite(expiresAt) && Date.now() >= expiresAt;
  const isAuthenticated = Boolean(token) && !isExpired;

  if (!isAuthenticated && isProtectedPath(pathname)) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.search = "";
    loginUrl.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthenticated && AUTH_PATHS.has(pathname)) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/calculator/focused";
    dashboardUrl.search = "";
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/calculator/:path*", "/history/:path*", "/billing/:path*", "/login", "/signup"],
};
