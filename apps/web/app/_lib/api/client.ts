import { toApiClientError } from "./errors";
import { clearAuthSession } from "../auth/session";

const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "").replace(/\/$/, "");

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
  signal?: AbortSignal;
};

async function parseJsonBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export async function requestJson<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
  const { method = "GET", body, token, signal } = options;

  const headers = new Headers();
  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const target = path.startsWith("/") ? path : `/${path}`;

  const response = await fetch(`${GATEWAY_BASE_URL}${target}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  handleUnauthorized(response, Boolean(token));

  const payload = await parseJsonBody(response);

  if (!response.ok) {
    throw toApiClientError(response, payload);
  }

  return payload as TResponse;
}

export function handleUnauthorized(response: Response, hasAccessToken: boolean) {
  if (response.status !== 401 || !hasAccessToken || typeof window === "undefined") {
    return;
  }

  clearAuthSession();

  if (window.location.pathname === "/login" || window.location.pathname === "/signup") {
    return;
  }

  const currentPath = `${window.location.pathname}${window.location.search}`;
  window.location.assign(`/login?next=${encodeURIComponent(currentPath)}`);
}
