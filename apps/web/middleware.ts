import { NextResponse, type NextRequest } from "next/server";
import { MOCK_AUTH_COOKIE } from "./app/_lib/mock-auth";

const AUTH_PATHS = new Set(["/login", "/signup"]);

function isProtectedPath(pathname: string) {
  return pathname.startsWith("/calculator") || pathname.startsWith("/history") || pathname.startsWith("/billing");
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const isAuthenticated = Boolean(request.cookies.get(MOCK_AUTH_COOKIE)?.value);

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
