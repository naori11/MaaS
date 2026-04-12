import type { GatewayErrorEnvelope } from "./types";

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(message: string, options: { status: number; code: string; requestId: string | null }) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseGatewayError(payload: unknown): GatewayErrorEnvelope | null {
  if (!isRecord(payload)) {
    return null;
  }

  const error = payload.error;
  if (!isRecord(error)) {
    return null;
  }

  const code = error.code;
  const message = error.message;

  if (typeof code !== "string" || typeof message !== "string") {
    return null;
  }

  const request_id = typeof payload.request_id === "string" ? payload.request_id : undefined;

  return {
    error: {
      code,
      message,
    },
    request_id,
  };
}

export function toApiClientError(response: Response, payload: unknown): ApiClientError {
  const parsed = parseGatewayError(payload);
  const fallbackMessage = response.statusText || "Gateway request failed";

  return new ApiClientError(parsed?.error.message ?? fallbackMessage, {
    status: response.status,
    code: parsed?.error.code ?? "internal_error",
    requestId: parsed?.request_id ?? null,
  });
}
