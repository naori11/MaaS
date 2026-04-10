export const MOCK_AUTH_COOKIE = "maas_mock_auth";
const MOCK_AUTH_VALUE = "1";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function setMockAuthCookie() {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${MOCK_AUTH_COOKIE}=${MOCK_AUTH_VALUE}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
}

export function clearMockAuthCookie() {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${MOCK_AUTH_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function isMockAuthenticatedInBrowser() {
  if (typeof document === "undefined") {
    return false;
  }

  return document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .some((cookie) => cookie.startsWith(`${MOCK_AUTH_COOKIE}=`));
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
