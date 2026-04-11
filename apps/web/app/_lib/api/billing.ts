import type { BackendBillingPlanName, BackendSubscribablePlanName } from "../billing/plan-mapper";

const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:4000").replace(/\/$/, "");
const AUTH_TOKEN_COOKIE = "maas_auth_token";
const AUTH_TOKEN_TYPE_COOKIE = "maas_auth_token_type";

export type BillingStatus = {
  plan_name: BackendBillingPlanName;
  status: "active" | "pending_payment";
  expires_at: string | null;
};

export type SubscribeResponse = {
  invoice_url: string;
};

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const entry = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`));

  if (!entry) {
    return null;
  }

  return decodeURIComponent(entry.slice(name.length + 1));
}

function getAuthorizationHeaderValue(): string | null {
  const token = readCookie(AUTH_TOKEN_COOKIE);

  if (!token) {
    return null;
  }

  const tokenType = readCookie(AUTH_TOKEN_TYPE_COOKIE) ?? "bearer";
  const normalizedType = tokenType.toLowerCase() === "bearer" ? "Bearer" : tokenType;

  return `${normalizedType} ${token}`;
}

async function billingRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const target = path.startsWith("/") ? path : `/${path}`;
  const authorization = getAuthorizationHeaderValue();

  const response = await fetch(`${GATEWAY_BASE_URL}${target}`, {
    credentials: "include",
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authorization ? { Authorization: authorization } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = "Billing request failed.";

    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      if (payload?.error?.message) {
        message = payload.error.message;
      }
    } catch {
      // ignore parse failures and keep fallback message
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function getBillingStatus() {
  return billingRequest<BillingStatus>("/api/v1/billing/status", {
    method: "GET",
  });
}

export function subscribeToPlan(planName: BackendSubscribablePlanName) {
  return billingRequest<SubscribeResponse>("/api/v1/billing/subscribe", {
    method: "POST",
    body: JSON.stringify({
      plan_name: planName,
    }),
  });
}
