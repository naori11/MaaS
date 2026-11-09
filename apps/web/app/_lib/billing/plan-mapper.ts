export type UiBillingPlanName = "Hobby" | "Pro" | "Enterprise";
export type BackendBillingPlanName = "Hobby" | "Pro" | "Enterprise" | "Free" | "Standard" | "Premium";
export type BackendSubscribablePlanName = "Pro";

const backendToUiPlanMap: Record<string, UiBillingPlanName> = {
  Hobby: "Hobby",
  Pro: "Pro",
  Enterprise: "Enterprise",
  Free: "Hobby",
  Standard: "Pro",
  Premium: "Enterprise",
};

export function mapUiPlanToBackendPlan(planName: UiBillingPlanName): "Hobby" | "Pro" | "Enterprise" {
  return planName;
}

export function mapBackendPlanToUiPlan(planName: string): UiBillingPlanName {
  return backendToUiPlanMap[planName] || "Hobby";
}

export function toSubscribableBackendPlan(planName: Exclude<UiBillingPlanName, "Hobby">): BackendSubscribablePlanName {
  if (planName === "Pro") {
    return "Pro";
  }

  throw new Error(`${planName} cannot be used for subscribe requests.`);
}
