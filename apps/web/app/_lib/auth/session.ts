import { clearAuthCookies, readAuthTokenFromBrowserCookies, writeAuthCookies } from "./cookies";

export type AuthSession = {
  accessToken: string;
  tokenType: string;
  expiresAtSeconds: number;
};

function nowInSeconds() {
  return Math.floor(Date.now() / 1000);
}

function parseTokenType(tokenType: string): string {
  const normalized = tokenType.trim().toLowerCase();
  return normalized || "bearer";
}

function parseExpiresAt(expiresInSeconds: number): number {
  return nowInSeconds() + Math.max(1, expiresInSeconds);
}

export function setAuthSession(payload: { accessToken: string; tokenType: string; expiresInSeconds: number }): AuthSession {
  const session: AuthSession = {
    accessToken: payload.accessToken,
    tokenType: parseTokenType(payload.tokenType),
    expiresAtSeconds: parseExpiresAt(payload.expiresInSeconds),
  };

  writeAuthCookies({
    token: session.accessToken,
    tokenType: session.tokenType,
    expiresInSeconds: payload.expiresInSeconds,
  });

  return session;
}

export function clearAuthSession() {
  clearAuthCookies();
}

export function getAuthTokenFromBrowserSession(): string | null {
  return readAuthTokenFromBrowserCookies();
}
