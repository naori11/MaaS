import type { NextRequest } from "next/server";

export const AUTH_TOKEN_COOKIE = "maas_auth_token";
export const AUTH_TOKEN_TYPE_COOKIE = "maas_auth_token_type";
export const AUTH_EXPIRES_AT_COOKIE = "maas_auth_expires_at";

function maxAgeToExpiresAtSeconds(maxAgeSeconds: number): string {
  return String(Math.floor(Date.now() / 1000) + maxAgeSeconds);
}

function parseDocumentCookies(): Map<string, string> {
  if (typeof document === "undefined") {
    return new Map();
  }

  return document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .filter(Boolean)
    .reduce((acc, cookie) => {
      const separatorIndex = cookie.indexOf("=");
      if (separatorIndex === -1) {
        return acc;
      }

      const name = cookie.slice(0, separatorIndex).trim();
      const value = cookie.slice(separatorIndex + 1).trim();
      acc.set(name, decodeURIComponent(value));
      return acc;
    }, new Map<string, string>());
}

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax`;
}

function clearCookie(name: string) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

export function writeAuthCookies(payload: { token: string; tokenType: string; expiresInSeconds: number }) {
  const maxAgeSeconds = Math.max(1, payload.expiresInSeconds);

  setCookie(AUTH_TOKEN_COOKIE, payload.token, maxAgeSeconds);
  setCookie(AUTH_TOKEN_TYPE_COOKIE, payload.tokenType, maxAgeSeconds);
  setCookie(AUTH_EXPIRES_AT_COOKIE, maxAgeToExpiresAtSeconds(maxAgeSeconds), maxAgeSeconds);
}

export function clearAuthCookies() {
  clearCookie(AUTH_TOKEN_COOKIE);
  clearCookie(AUTH_TOKEN_TYPE_COOKIE);
  clearCookie(AUTH_EXPIRES_AT_COOKIE);
}

export function readAuthTokenFromBrowserCookies(): string | null {
  const cookies = parseDocumentCookies();
  return cookies.get(AUTH_TOKEN_COOKIE) ?? null;
}

export function readAuthTokenFromRequestCookies(request: NextRequest): string | null {
  return request.cookies.get(AUTH_TOKEN_COOKIE)?.value ?? null;
}

export function readAuthTokenFromCookieStore(cookieStore: { get: (name: string) => { value: string } | undefined }): string | null {
  return cookieStore.get(AUTH_TOKEN_COOKIE)?.value ?? null;
}
