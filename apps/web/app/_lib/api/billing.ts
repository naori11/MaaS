import type { BackendBillingPlanName, BackendSubscribablePlanName } from "../billing/plan-mapper";
import { getAuthTokenFromBrowserSession } from "../auth/session";
import { handleUnauthorized } from "./client";

const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "").replace(/\/$/, "");

export type BillingStatus = {
  plan_name: BackendBillingPlanName;
  status: "active" | "pending_payment";
  expires_at: string | null;
};

export type SubscribeResponse = {
  components_sdk_key: string;
};

function getAuthorizationHeaderValue(): string | null {
  const token = getAuthTokenFromBrowserSession();

  if (!token) {
    return null;
  }

  return `Bearer ${token}`;
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

  handleUnauthorized(response, Boolean(authorization));

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
