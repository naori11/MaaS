export type UiBillingPlanName = "Hobby" | "Pro" | "Enterprise";
export type BackendBillingPlanName = "Free" | "Standard" | "Premium";
export type BackendSubscribablePlanName = Exclude<BackendBillingPlanName, "Free">;

const uiToBackendPlanMap: Record<UiBillingPlanName, BackendBillingPlanName> = {
  Hobby: "Free",
  Pro: "Standard",
  Enterprise: "Premium",
};

const backendToUiPlanMap: Record<BackendBillingPlanName, UiBillingPlanName> = {
  Free: "Hobby",
  Standard: "Pro",
  Premium: "Enterprise",
};

export function mapUiPlanToBackendPlan(planName: UiBillingPlanName): BackendBillingPlanName {
  return uiToBackendPlanMap[planName];
}

export function mapBackendPlanToUiPlan(planName: BackendBillingPlanName): UiBillingPlanName {
  return backendToUiPlanMap[planName];
}

export function toSubscribableBackendPlan(planName: Exclude<UiBillingPlanName, "Hobby">): BackendSubscribablePlanName {
  const mappedPlan = mapUiPlanToBackendPlan(planName);

  if (mappedPlan === "Free") {
    throw new Error("Hobby cannot be used for subscribe requests.");
  }

  return mappedPlan;
}
