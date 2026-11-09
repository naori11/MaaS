import type { BackendBillingPlanName, BackendSubscribablePlanName } from "../billing/plan-mapper";
import { getAuthTokenFromBrowserSession } from "../auth/session";
import { handleUnauthorized } from "./client";

const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "").replace(/\/$/, "");

export type TrialInfo = {
  eligible: boolean;
  is_active: boolean;
  days_remaining: number | null;
  expires_at: string | null;
};

export type UsageInfo = {
  used: number;
  limit: number | null;
  unlimited: boolean;
  next_reset_at: string;
};

export type BillingStatus = {
  plan_name: BackendBillingPlanName;
  status: "active" | "pending_payment" | "past_due" | "canceled" | "expired";
  current_period_end?: string | null;
  expires_at: string | null;
  current_period_start?: string | null;
  cancel_at_period_end?: boolean;
  grace_period_deadline?: string | null;
  trial?: TrialInfo;
  usage?: UsageInfo;
  can_cancel?: boolean;
};

export type SubscribeResponse = {
  components_sdk_key: string;
};

export type TrialStartResponse = {
  status: string;
  expires_at: string;
  days_remaining: number;
};

export type PaymentRecord = {
  id: string;
  date: string;
  amount: string;
  raw_amount: number;
  currency: string;
  status: string;
  description: string;
};

export type ReceiptResponse = {
  receipt_id: string;
  user_id: string;
  amount: string;
  currency: string;
  status: string;
  date: string;
  description: string;
  receipt_text: string;
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

export function startProTrial() {
  return billingRequest<TrialStartResponse>("/api/v1/billing/trial/start", {
    method: "POST",
  });
}

export function cancelSubscription() {
  return billingRequest<BillingStatus>("/api/v1/billing/cancel", {
    method: "POST",
  });
}

export function getPaymentHistory() {
  return billingRequest<PaymentRecord[]>("/api/v1/billing/history", {
    method: "GET",
  });
}

export function getReceipt(paymentId: string) {
  return billingRequest<ReceiptResponse>(`/api/v1/billing/receipts/${paymentId}`, {
    method: "GET",
  });
}

export function getBillingUsage() {
  return billingRequest<UsageInfo>("/api/v1/billing/usage", {
    method: "GET",
  });
}
