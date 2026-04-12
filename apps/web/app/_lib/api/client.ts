import { toApiClientError } from "./errors";

const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:4000").replace(/\/$/, "");

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

  const payload = await parseJsonBody(response);

  if (!response.ok) {
    throw toApiClientError(response, payload);
  }

  return payload as TResponse;
}
