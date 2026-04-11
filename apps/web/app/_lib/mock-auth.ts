export const AUTH_TOKEN_COOKIE = "maas_auth_token";
export const AUTH_TOKEN_TYPE_COOKIE = "maas_auth_token_type";
export const AUTH_EXPIRES_AT_COOKIE = "maas_auth_expires_at";

const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

const readCookie = (name: string) => {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(`${name}=`));

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(cookie.slice(name.length + 1));
};

const writeCookie = (name: string, value: string, maxAgeSeconds: number) => {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax`;
};

export function setAuthSession(input: { accessToken: string; tokenType: string; expiresInSeconds: number }) {
  if (typeof document === "undefined") {
    return;
  }

  const expiresInSeconds = Number.isFinite(input.expiresInSeconds) && input.expiresInSeconds > 0 ? input.expiresInSeconds : COOKIE_MAX_AGE_SECONDS;
  const expiresAt = Date.now() + expiresInSeconds * 1000;

  writeCookie(AUTH_TOKEN_COOKIE, input.accessToken, expiresInSeconds);
  writeCookie(AUTH_TOKEN_TYPE_COOKIE, input.tokenType, expiresInSeconds);
  writeCookie(AUTH_EXPIRES_AT_COOKIE, String(expiresAt), expiresInSeconds);
}

export function clearAuthSession() {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${AUTH_TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
  document.cookie = `${AUTH_TOKEN_TYPE_COOKIE}=; path=/; max-age=0; samesite=lax`;
  document.cookie = `${AUTH_EXPIRES_AT_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function getAuthTokenFromBrowserSession() {
  return readCookie(AUTH_TOKEN_COOKIE);
}

export function getAuthTokenTypeFromBrowserSession() {
  const tokenType = readCookie(AUTH_TOKEN_TYPE_COOKIE) ?? "bearer";

  return tokenType.toLowerCase() === "bearer" ? "Bearer" : tokenType;
}

export function hasActiveBrowserSession() {
  const token = getAuthTokenFromBrowserSession();

  if (!token) {
    return false;
  }

  const expiresAtRaw = readCookie(AUTH_EXPIRES_AT_COOKIE);

  if (!expiresAtRaw) {
    return true;
  }

  const expiresAt = Number(expiresAtRaw);

  if (!Number.isFinite(expiresAt)) {
    return true;
  }

  return Date.now() < expiresAt;
}

export function resolvePostAuthRedirect(nextPath: string | null | undefined) {
  if (!nextPath) {
    return "/calculator/focused";
  }

  if (!nextPath.startsWith("/")) {
    return "/calculator/focused";
  }

  if (nextPath.startsWith("//") || nextPath.includes("://")) {
    return "/calculator/focused";
  }

  return nextPath;
}
