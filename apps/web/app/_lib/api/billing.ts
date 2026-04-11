import type { BackendBillingPlanName, BackendSubscribablePlanName } from "../billing/plan-mapper";

export type BillingStatus = {
  plan_name: BackendBillingPlanName;
  status: "active" | "pending_payment";
  expires_at: string | null;
};

export type SubscribeResponse = {
  invoice_url: string;
};

async function billingRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
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
