"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  MotionButton,
  MotionCard,
  MotionPresenceBlock,
  MotionSection,
  MotionStaggerContainer,
  MotionStaggerItem,
} from "../_components/motion/motion-primitives";
import { MOTION_DURATION, MOTION_EASE } from "../_lib/motion/tokens";
import {
  cancelSubscription,
  getBillingStatus,
  getPaymentHistory,
  getReceipt,
  startProTrial,
  subscribeToPlan,
  type BillingStatus,
  type PaymentRecord,
} from "../_lib/api/billing";
import { mapBackendPlanToUiPlan, type UiBillingPlanName } from "../_lib/billing/plan-mapper";

type Plan = {
  name: UiBillingPlanName;
  badge: string;
  price: string;
  period: string;
  cta: string;
  featured: boolean;
  features: string[];
  unavailable: number[];
};

const plans: Plan[] = [
  {
    name: "Hobby",
    badge: "Free Tier",
    price: "₱0",
    period: "/month",
    cta: "Current Plan",
    featured: false,
    features: [
      "50 calculations per day across all operations",
      "7 days of synced history",
      "Multi-threaded solving",
    ],
    unavailable: [],
  },
  {
    name: "Pro",
    badge: "Recommended",
    price: "₱99",
    period: "/month",
    cta: "Upgrade to Pro",
    featured: true,
    features: [
      "Unlimited calculations",
      "Full private synced history",
      "CSV export",
      "Priority calculation queuing",
    ],
    unavailable: [],
  },
  {
    name: "Enterprise",
    badge: "Scale",
    price: "Custom",
    period: "",
    cta: "Contact Sales",
    featured: false,
    features: [
      "Custom volume agreements",
      "Dedicated infrastructure",
      "Enterprise SLA guarantees",
    ],
    unavailable: [],
  },
];

const paymentMethods = ["Visa ending in 4421", "Mastercard ending in 1102", "Amex ending in 9014"];

const XENDIT_COMPONENTS_SCRIPT_SRC = "https://assets.xendit.co/components/v0.0.21/index.umd.js";

type XenditComponentsInstance = {
  createChannelPickerComponent: () => HTMLElement;
  submit: () => void;
  addEventListener: (eventName: string, callback: () => void) => void;
};

type XenditWindow = Window & {
  Xendit?: {
    XenditComponents?: new (options: { componentsSdkKey: string }) => XenditComponentsInstance;
  };
};

function ensureXenditComponentsScript() {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }

  if ((window as XenditWindow).Xendit?.XenditComponents) {
    return Promise.resolve();
  }

  return new Promise<void>((resolve, reject) => {
    const createScript = () => {
      const script = document.createElement("script");
      script.src = XENDIT_COMPONENTS_SCRIPT_SRC;
      script.async = true;
      script.dataset.xenditComponentsState = "loading";
      script.addEventListener(
        "load",
        () => {
          script.dataset.xenditComponentsState = "loaded";
          resolve();
        },
        { once: true },
      );
      script.addEventListener(
        "error",
        () => {
          script.dataset.xenditComponentsState = "error";
          reject(new Error("Unable to load Xendit Components SDK."));
        },
        { once: true },
      );
      document.head.appendChild(script);
    };

    const existingScript = document.querySelector(`script[src="${XENDIT_COMPONENTS_SCRIPT_SRC}"]`) as HTMLScriptElement | null;

    if (existingScript) {
      if ((window as XenditWindow).Xendit?.XenditComponents || existingScript.dataset.xenditComponentsState === "loaded") {
        resolve();
        return;
      }

      if (existingScript.dataset.xenditComponentsState === "error") {
        existingScript.remove();
        createScript();
        return;
      }

      existingScript.addEventListener("load", () => resolve(), { once: true });
      existingScript.addEventListener("error", () => reject(new Error("Unable to load Xendit Components SDK.")), { once: true });
      return;
    }

    createScript();
  });
}

export default function BillingPage() {
  const shouldReduceMotion = useReducedMotion();
  const [currentPlan, setCurrentPlan] = useState<UiBillingPlanName>("Hobby");
  const [billingDetails, setBillingDetails] = useState<BillingStatus | null>(null);
  const [billingStatus, setBillingStatus] = useState<"active" | "pending_payment" | "past_due" | "canceled" | "expired">("active");
  const [pendingPlan, setPendingPlan] = useState<Exclude<UiBillingPlanName, "Hobby"> | null>(null);
  const [paymentMethod, setPaymentMethod] = useState(paymentMethods[0]);
  const [showPaymentOptions, setShowPaymentOptions] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [subscribingPlan, setSubscribingPlan] = useState<Exclude<UiBillingPlanName, "Hobby"> | null>(null);
  const [isStartingTrial, setIsStartingTrial] = useState(false);
  const [isCanceling, setIsCanceling] = useState(false);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [sdkKey, setSdkKey] = useState<string | null>(null);
  const [paymentHistory, setPaymentHistory] = useState<PaymentRecord[]>([]);
  const checkoutContainerRef = useRef<HTMLDivElement | null>(null);
  const xenditInstanceRef = useRef<XenditComponentsInstance | null>(null);

  const fetchStatusAndHistory = async () => {
    try {
      const status = await getBillingStatus();
      setBillingDetails(status);

      const mappedPlan = mapBackendPlanToUiPlan(status.plan_name);
      setCurrentPlan(mappedPlan);
      setBillingStatus(status.status);

      if (status.status === "pending_payment") {
        const pendingActivationPlan = mappedPlan === "Hobby" ? null : mappedPlan;
        setPendingPlan(pendingActivationPlan);
        setStatusMessage(
          pendingActivationPlan
            ? `Payment for ${pendingActivationPlan} is pending. Complete checkout to activate your plan.`
            : "Payment is pending. Complete checkout to activate your plan.",
        );
      } else if (status.status === "past_due") {
        setPendingPlan(null);
        setStatusMessage(
          `Renewal payment failed. You retain Pro access during the 7-day grace period until ${status.grace_period_deadline ? new Date(status.grace_period_deadline).toLocaleDateString() : "grace period end"}.`,
        );
      } else {
        setPendingPlan(null);
        setStatusMessage("");
      }

      // Load history
      try {
        const history = await getPaymentHistory();
        setPaymentHistory(history);
      } catch {
        // history may be empty for new accounts
      }
    } catch (error) {
      setStatusMessage("");
      setErrorMessage(error instanceof Error ? error.message : "Unable to load billing status.");
    }
  };

  useEffect(() => {
    let isMounted = true;
    setStatusMessage("Loading subscription status...");
    setErrorMessage("");

    void (async () => {
      await fetchStatusAndHistory();
      if (isMounted) {
        setStatusMessage("");
      }
    })();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!sdkKey || !checkoutContainerRef.current) {
      return;
    }

    let cancelled = false;
    let pollingTimeoutId: ReturnType<typeof setTimeout> | null = null;
    const currentContainer = checkoutContainerRef.current;

    const mountCheckout = async () => {
      try {
        await ensureXenditComponentsScript();

        if (cancelled) {
          return;
        }

        const xenditWindow = window as XenditWindow;
        const XenditComponents = xenditWindow.Xendit?.XenditComponents;

        if (!XenditComponents) {
          throw new Error("Xendit Components SDK is unavailable.");
        }

        const instance = new XenditComponents({ componentsSdkKey: sdkKey });
        xenditInstanceRef.current = instance;
        const picker = instance.createChannelPickerComponent();

        if (!checkoutContainerRef.current) {
          return;
        }

        checkoutContainerRef.current.replaceChildren(picker);

        const pollForActiveStatus = async (maxAttempts = 10, intervalMs = 3000) => {
          let attempts = 0;

          const poll = async (): Promise<void> => {
            if (cancelled) {
              return;
            }

            attempts++;

            try {
              const status = await getBillingStatus();
              const mappedPlan = mapBackendPlanToUiPlan(status.plan_name);

              if (status.status === "active") {
                setCurrentPlan(mappedPlan);
                setBillingStatus("active");
                setPendingPlan(null);
                setBillingDetails(status);
                setStatusMessage("Payment completed. Your Pro plan is now active!");
                setIsCheckingOut(false);
                setSdkKey(null);
                await fetchStatusAndHistory();
                return;
              }

              if (attempts >= maxAttempts) {
                setCurrentPlan(mappedPlan);
                setBillingStatus(status.status);
                setPendingPlan(status.status === "pending_payment" && mappedPlan !== "Hobby" ? mappedPlan : null);
                setStatusMessage("Payment is processing. Please refresh the page to check your updated status.");
                setIsCheckingOut(false);
                setSdkKey(null);
                return;
              }

              setStatusMessage(`Payment processing... (checking ${attempts}/${maxAttempts})`);
              pollingTimeoutId = setTimeout(() => void poll(), intervalMs);
            } catch {
              if (attempts >= maxAttempts) {
                setStatusMessage("Payment completed. Refresh to confirm updated status.");
                setIsCheckingOut(false);
                setSdkKey(null);
                return;
              }

              pollingTimeoutId = setTimeout(() => void poll(), intervalMs);
            }
          };

          await poll();
        };

        instance.addEventListener("session-complete", () => {
          setStatusMessage("Payment completed. Verifying status with backend...");
          void pollForActiveStatus();
        });

        instance.addEventListener("session-expired-or-canceled", () => {
          setIsCheckingOut(false);
          setSdkKey(null);
          setPendingPlan(null);
          setBillingStatus("active");
          setStatusMessage("Payment was canceled or expired. Please try again.");
        });

        instance.addEventListener("fatal-error", () => {
          setIsCheckingOut(false);
          setSdkKey(null);
          setErrorMessage("Checkout failed to initialize. Please check your connection or try again.");
        });

        instance.addEventListener("will-redirect", () => {
          setStatusMessage("Completing payment...");
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setIsCheckingOut(false);
        setSdkKey(null);
        setErrorMessage(error instanceof Error ? error.message : "Unable to initialize embedded checkout.");
      }
    };

    void mountCheckout();

    return () => {
      cancelled = true;
      if (pollingTimeoutId) {
        clearTimeout(pollingTimeoutId);
      }
      if (currentContainer) {
        currentContainer.replaceChildren();
      }
      xenditInstanceRef.current = null;
    };
  }, [sdkKey]);

  const handleStartTrial = async () => {
    setIsStartingTrial(true);
    setErrorMessage("");
    setStatusMessage("Starting your 7-day Pro preview...");

    try {
      const response = await startProTrial();
      setStatusMessage(`Pro preview activated! Enjoy unlimited calculations for ${response.days_remaining} days.`);
      await fetchStatusAndHistory();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to start Pro preview.");
    } finally {
      setIsStartingTrial(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm("Are you sure you want to cancel renewal at the end of the current billing period? You will retain access until the period ends.")) {
      return;
    }

    setIsCanceling(true);
    setErrorMessage("");
    try {
      await cancelSubscription();
      setStatusMessage("Renewal cancelled. You will retain Pro access through the end of your billing period.");
      await fetchStatusAndHistory();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to cancel subscription.");
    } finally {
      setIsCanceling(false);
    }
  };

  const handleSelectPlan = async (plan: UiBillingPlanName) => {
    if (plan === "Hobby") {
      return;
    }

    if (plan === "Enterprise") {
      setStatusMessage("Please contact our sales team using the link below for custom enterprise plans.");
      return;
    }

    if (plan === currentPlan && !(billingStatus === "pending_payment" && pendingPlan === plan)) {
      return;
    }

    setErrorMessage("");
    setStatusMessage("");
    setSubscribingPlan(plan);

    try {
      const response = await subscribeToPlan("Pro");
      setBillingStatus("pending_payment");
      setPendingPlan("Pro");
      setSdkKey(response.components_sdk_key);
      setIsCheckingOut(true);
      setStatusMessage("Complete your embedded checkout to activate Pro.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to start checkout.");
    } finally {
      setSubscribingPlan(null);
    }
  };

  const handleSelectPaymentMethod = (method: string) => {
    setPaymentMethod(method);
    setShowPaymentOptions(false);
  };

  const handleSubmitEmbeddedCheckout = () => {
    xenditInstanceRef.current?.submit();
  };

  const handleDownloadInvoice = async (invoiceId: string) => {
    try {
      const receipt = await getReceipt(invoiceId);
      const blob = new Blob([receipt.receipt_text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `receipt-${receipt.receipt_id}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDownloadMessage(`Receipt ${invoiceId} downloaded.`);
    } catch {
      setDownloadMessage(`Receipt ${invoiceId} downloaded.`);
    }

    setTimeout(() => {
      setDownloadMessage("");
    }, 2000);
  };

  const isTrialActive = Boolean(billingDetails?.trial?.is_active);
  const isTrialEligible = Boolean(billingDetails?.trial?.eligible && currentPlan === "Hobby");
  const cancelAtPeriodEnd = Boolean(billingDetails?.cancel_at_period_end);

  return (
    <>
      <MotionSection>
        <p className="mb-3 text-xs font-bold uppercase tracking-[0.15em] text-[#b60055] sm:mb-4">Subscription Management</p>
        <h2 className="mb-3 text-3xl font-extrabold leading-tight tracking-tight text-[#203044] sm:mb-4 sm:text-4xl md:text-5xl md:leading-none">
          with surgical precision. <span className="text-[#68788f]">Choose your tier.</span>
        </h2>
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold text-[#4d5d73]" aria-live="polite">
            Current plan: <span className="text-[#b60055]">{currentPlan}</span>
          </p>
          {isTrialActive ? (
            <span className="rounded-full bg-[#b60055]/10 px-3 py-0.5 text-xs font-bold text-[#b60055]">
              Pro Preview: {billingDetails?.trial?.days_remaining} days remaining
            </span>
          ) : null}
          {cancelAtPeriodEnd ? (
            <span className="rounded-full bg-amber-500/10 px-3 py-0.5 text-xs font-bold text-amber-700">
              Cancels on {billingDetails?.current_period_end ? new Date(billingDetails.current_period_end).toLocaleDateString() : "period end"}
            </span>
          ) : null}
        </div>
        {billingStatus === "pending_payment" && pendingPlan ? (
          <p className="mb-2 text-xs font-semibold text-[#b60055]" aria-live="polite">
            Pending activation: {pendingPlan}
          </p>
        ) : null}
        {statusMessage ? (
          <p className="mb-2 rounded-lg border border-[#9eaec7]/20 bg-white px-3 py-2 text-xs font-semibold text-[#4d5d73]" role="status">
            {statusMessage}
          </p>
        ) : null}
        {errorMessage ? (
          <p className="mb-10 rounded-lg border border-[#b60055]/15 bg-[#b60055]/5 px-3 py-2 text-xs font-semibold text-[#b60055] sm:mb-12 md:mb-14" role="alert">
            {errorMessage}
          </p>
        ) : (
          <div className="mb-10 sm:mb-12 md:mb-14" />
        )}
      </MotionSection>

      {isCheckingOut ? (
        <MotionCard className="mb-8 rounded-3xl border border-[#b60055]/20 bg-white p-5 sm:p-6 md:p-7">
          <h3 className="mb-3 text-lg font-bold text-[#203044]">Embedded Checkout</h3>
          <p className="mb-4 text-sm font-medium text-[#4d5d73]">Choose a payment method below and submit payment without leaving this page.</p>
          <div ref={checkoutContainerRef} id="xendit-checkout-container" className="min-h-24 rounded-xl border border-[#9eaec7]/20 bg-[#f7faff] p-3" />
          <MotionButton
            type="button"
            onClick={handleSubmitEmbeddedCheckout}
            className="maas-touch-target mt-4 w-full rounded-xl bg-[#203044] px-5 py-3 text-sm font-bold text-white"
          >
            Pay Now (₱99.00/mo)
          </MotionButton>
        </MotionCard>
      ) : null}

      <MotionStaggerContainer className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:gap-6 xl:grid-cols-3 xl:gap-8">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.name;
          const isPending = billingStatus === "pending_payment" && pendingPlan === plan.name;
          const isSubmitting = subscribingPlan === plan.name;

          return (
            <MotionStaggerItem key={plan.name} className={plan.featured ? "md:col-span-2 xl:col-span-1" : undefined}>
              <MotionCard
                className={`flex h-full flex-col justify-between rounded-3xl p-5 sm:p-6 md:p-7 lg:p-8 ${
                  plan.featured
                    ? "relative overflow-hidden border-2 border-[#b60055]/10 bg-white shadow-[0px_20px_40px_rgba(32,48,68,0.06)]"
                    : "bg-[#eaf1ff]"
                }`}
              >
                {plan.featured ? (
                  <div className="absolute right-0 top-0 p-3 sm:p-4">
                    <span className="maas-enterprise-gradient rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-white">
                      {plan.badge}
                    </span>
                  </div>
                ) : null}

                <div>
                  <span
                    className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${
                      plan.featured ? "bg-[#b60055]/10 text-[#b60055]" : "bg-[#c9deff] text-[#4d5d73]"
                    }`}
                  >
                    {plan.name}
                  </span>

                  <h3 className="mt-4 text-2xl font-bold sm:text-3xl">{plan.name}</h3>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-3xl font-black sm:text-4xl">{plan.price}</span>
                    {plan.period ? <span className="text-sm text-[#4d5d73]">{plan.period}</span> : null}
                  </div>

                  <ul className="mt-6 space-y-4 sm:mt-8 sm:space-y-5 md:space-y-6">
                    {plan.features.map((feature, index) => {
                      const unavailable = plan.unavailable.includes(index);
                      return (
                        <li key={feature} className={`flex items-start gap-3 ${unavailable ? "opacity-30" : ""}`}>
                          <span
                            className="material-symbols-outlined mt-0.5"
                            style={unavailable ? undefined : { fontVariationSettings: "'FILL' 1" }}
                          >
                            {unavailable ? "cancel" : "check_circle"}
                          </span>
                          <span className="text-sm font-medium">{feature}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                <div className="mt-8 space-y-3 sm:mt-10 md:mt-12">
                  {plan.name === "Pro" && isTrialEligible ? (
                    <MotionButton
                      type="button"
                      onClick={() => void handleStartTrial()}
                      disabled={isStartingTrial}
                      className="maas-touch-target w-full rounded-xl border-2 border-[#b60055] bg-[#b60055]/5 px-5 py-2.5 text-xs font-bold text-[#b60055] transition hover:bg-[#b60055]/10"
                    >
                      {isStartingTrial ? "Activating Preview..." : "Try Pro free (7 days)"}
                    </MotionButton>
                  ) : null}

                  {plan.name === "Pro" && isCurrent && !isTrialActive && billingDetails?.can_cancel && !cancelAtPeriodEnd ? (
                    <MotionButton
                      type="button"
                      onClick={() => void handleCancelSubscription()}
                      disabled={isCanceling}
                      className="maas-touch-target w-full rounded-xl border border-rose-300 bg-white px-4 py-2 text-xs font-bold text-rose-700 transition hover:bg-rose-50"
                    >
                      {isCanceling ? "Cancelling..." : "Cancel Renewal"}
                    </MotionButton>
                  ) : null}

                  <MotionButton
                    type="button"
                    onClick={() => void handleSelectPlan(plan.name)}
                    disabled={isSubmitting || plan.name === "Hobby"}
                    className={`maas-touch-target w-full rounded-xl px-5 py-3 font-bold transition disabled:opacity-70 ${
                      isCurrent
                        ? "border-2 border-[#b60055] bg-white text-[#b60055]"
                        : plan.featured
                          ? "maas-enterprise-gradient text-white"
                          : plan.name === "Enterprise"
                            ? "bg-[#203044] text-[#f4f6ff]"
                            : "bg-[#d2e4ff] text-[#203044]"
                    }`}
                  >
                    {isCurrent
                      ? (isPending ? "Resume Payment" : isTrialActive ? "Pro Preview Active" : "Current Plan")
                      : isPending
                        ? "Pending Activation"
                        : isSubmitting
                          ? "Initializing Checkout..."
                          : plan.cta}
                  </MotionButton>
                </div>
              </MotionCard>
            </MotionStaggerItem>
          );
        })}
      </MotionStaggerContainer>

      <section className="mt-12 grid grid-cols-1 items-start gap-6 md:mt-16 md:grid-cols-12 md:gap-8 lg:mt-24 lg:gap-12">
        <MotionCard className="md:col-span-7">
          <article className="rounded-3xl border border-[#9eaec7]/10 bg-[#eaf1ff]/50 p-5 sm:p-6 md:p-8 lg:p-10">
            <h4 className="mb-4 text-xl font-bold sm:mb-6 sm:text-2xl">Payment History</h4>
            {downloadMessage ? (
              <p className="mb-4 rounded-lg border border-[#b60055]/15 bg-[#b60055]/5 px-3 py-2 text-xs font-semibold text-[#b60055]" role="status">
                {downloadMessage}
              </p>
            ) : null}
            <div className="space-y-3 sm:space-y-4">
              {paymentHistory.length === 0 ? (
                <div className="rounded-xl bg-white p-5 text-center text-xs font-medium text-[#4d5d73]">
                  No payment transactions recorded yet.
                </div>
              ) : (
                paymentHistory.map((invoice, index) => (
                  <motion.div
                    key={invoice.id}
                    className="flex flex-col gap-3 rounded-xl bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
                    initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: shouldReduceMotion ? MOTION_DURATION.fast : MOTION_DURATION.base,
                      ease: MOTION_EASE.standard,
                      delay: shouldReduceMotion ? 0 : index * 0.04,
                    }}
                  >
                    <div className="flex items-center gap-3 sm:gap-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#c8d8f3]">
                        <span className="material-symbols-outlined text-[#3c4c61]">receipt</span>
                      </div>
                      <div>
                        <p className="text-sm font-bold">{invoice.description}</p>
                        <p className="text-[10px] font-medium uppercase text-[#68788f]">
                          {invoice.date ? new Date(invoice.date).toLocaleDateString() : ""} &bull; {invoice.status.toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 sm:gap-6">
                      <p className="text-sm font-bold">{invoice.amount}</p>
                      <MotionButton
                        type="button"
                        className="maas-touch-target text-xs font-bold text-[#b60055] hover:underline"
                        onClick={() => void handleDownloadInvoice(invoice.id)}
                      >
                        Download
                      </MotionButton>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </article>
        </MotionCard>

        <div className="space-y-6 md:col-span-5 md:space-y-8">
          <MotionCard>
            <article className="rounded-3xl border border-[#9eaec7]/10 bg-white p-5 shadow-sm sm:p-6 md:p-8">
              <div className="mb-5 flex items-center gap-3 sm:mb-6 sm:gap-4">
                <div className="maas-enterprise-gradient flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white">
                  <span className="material-symbols-outlined">credit_score</span>
                </div>
                <div className="min-w-0">
                  <h4 className="font-bold">Primary Method</h4>
                  <p className="truncate text-sm text-[#4d5d73]">{paymentMethod}</p>
                </div>
              </div>
              <MotionButton
                type="button"
                className="maas-touch-target w-full rounded-lg border-2 border-[#9eaec7]/20 px-4 py-3 text-sm font-bold"
                onClick={() => setShowPaymentOptions((value) => !value)}
              >
                {showPaymentOptions ? "Hide Payment Methods" : "Update Payment Method"}
              </MotionButton>
              <MotionPresenceBlock show={showPaymentOptions} className="mt-4">
                <div className="space-y-2">
                  {paymentMethods.map((method) => (
                    <MotionButton
                      key={method}
                      type="button"
                      onClick={() => handleSelectPaymentMethod(method)}
                      className="maas-touch-target w-full rounded-lg bg-[#eaf1ff] px-3 py-2 text-left text-xs font-semibold text-[#203044]"
                    >
                      {method}
                    </MotionButton>
                  ))}
                </div>
              </MotionPresenceBlock>
            </article>
          </MotionCard>

          <MotionCard>
            <article className="rounded-3xl border border-[#b60055]/10 bg-[#b60055]/5 p-5 sm:p-6 md:p-8">
              <h4 className="mb-2 font-bold">Need a custom math quota?</h4>
              <p className="mb-5 text-sm text-[#4d5d73] sm:mb-6">
                Our sales team can tailor a plan that fits your exact computational throughput needs.
              </p>
              <Link href="/signup" className="maas-touch-target group inline-flex items-center gap-2 text-sm font-bold text-[#b60055]">
                Talk to an expert
                <span className="material-symbols-outlined text-sm transition group-hover:translate-x-1">arrow_forward</span>
              </Link>
            </article>
          </MotionCard>
        </div>
      </section>
    </>
  );
}
