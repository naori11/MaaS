export type BillingPlanName = "Hobby" | "Pro" | "Enterprise";

export type BillingState = {
  currentPlan: BillingPlanName;
  paymentMethod: string;
};

const BILLING_STORAGE_KEY = "maas_mock_billing";

const defaultBillingState: BillingState = {
  currentPlan: "Hobby",
  paymentMethod: "Visa ending in 4421",
};

export function getDefaultBillingState() {
  return { ...defaultBillingState };
}

export function loadBillingState() {
  if (typeof window === "undefined") {
    return getDefaultBillingState();
  }

  const raw = window.localStorage.getItem(BILLING_STORAGE_KEY);
  if (!raw) {
    window.localStorage.setItem(BILLING_STORAGE_KEY, JSON.stringify(defaultBillingState));
    return getDefaultBillingState();
  }

  try {
    const parsed = JSON.parse(raw) as BillingState;
    if (!parsed.currentPlan || !parsed.paymentMethod) {
      return getDefaultBillingState();
    }

    return parsed;
  } catch {
    return getDefaultBillingState();
  }
}

export function saveBillingState(state: BillingState) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(BILLING_STORAGE_KEY, JSON.stringify(state));
}
