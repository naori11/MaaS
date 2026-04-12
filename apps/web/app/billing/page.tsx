"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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
import { getBillingStatus, subscribeToPlan } from "../_lib/api/billing";
import { mapBackendPlanToUiPlan, toSubscribableBackendPlan, type UiBillingPlanName } from "../_lib/billing/plan-mapper";

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
    badge: "Sandbox",
    price: "₱0",
    period: "/month",
    cta: "Start Computing",
    featured: false,
    features: ["10 additions/day. No subtraction.", "Public calculation history", "Multi-threaded solving"],
    unavailable: [2],
  },
  {
    name: "Pro",
    badge: "Growth",
    price: "₱50",
    period: "/month",
    cta: "Upgrade Now",
    featured: true,
    features: ["Unlimited basic math.", "Private result logs", "Priority equation queuing", "Algebraic support"],
    unavailable: [],
  },
  {
    name: "Enterprise",
    badge: "Scale",
    price: "₱250",
    period: "/month",
    cta: "Upgrade Now",
    featured: false,
    features: [
      "Dedicated servers for division.",
      "99.99% Calculus uptime SLA",
      "Unlimited seat licenses",
      "Custom formula integration",
    ],
    unavailable: [],
  },
];

const paymentMethods = ["Visa ending in 4421", "Mastercard ending in 1102", "Amex ending in 9014"];

export default function BillingPage() {
  const shouldReduceMotion = useReducedMotion();
  const [currentPlan, setCurrentPlan] = useState<UiBillingPlanName>("Hobby");
  const [billingStatus, setBillingStatus] = useState<"active" | "pending_payment">("active");
  const [pendingPlan, setPendingPlan] = useState<Exclude<UiBillingPlanName, "Hobby"> | null>(null);
  const [paymentMethod, setPaymentMethod] = useState(paymentMethods[0]);
  const [showPaymentOptions, setShowPaymentOptions] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [subscribingPlan, setSubscribingPlan] = useState<Exclude<UiBillingPlanName, "Hobby"> | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadStatus = async () => {
      setStatusMessage("Loading subscription status...");
      setErrorMessage("");

      try {
        const status = await getBillingStatus();

        if (!isMounted) {
          return;
        }

        const mappedPlan = mapBackendPlanToUiPlan(status.plan_name);

        if (status.status === "pending_payment") {
          const pendingActivationPlan = mappedPlan === "Hobby" ? null : mappedPlan;

          setBillingStatus("pending_payment");
          setCurrentPlan(mappedPlan);
          setPendingPlan(pendingActivationPlan);
          setStatusMessage(
            pendingActivationPlan
              ? `Payment for ${pendingActivationPlan} is pending. Complete checkout to activate your plan.`
              : "Payment is pending. Complete checkout to activate your plan.",
          );
        } else {
          setBillingStatus("active");
          setPendingPlan(null);
          setCurrentPlan(mappedPlan);
          setStatusMessage("");
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setStatusMessage("");
        setErrorMessage(error instanceof Error ? error.message : "Unable to load billing status.");
      }
    };

    void loadStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSelectPlan = async (plan: UiBillingPlanName) => {
    if (plan === currentPlan) {
      return;
    }

    setErrorMessage("");
    setStatusMessage("");

    if (plan === "Hobby") {
      setStatusMessage("Downgrades to Hobby are currently handled by support.");
      return;
    }

    setSubscribingPlan(plan);

    try {
      const response = await subscribeToPlan(toSubscribableBackendPlan(plan));
      setBillingStatus("pending_payment");
      setPendingPlan(plan);
      window.open(response.invoice_url, "_blank", "noopener,noreferrer");
      setStatusMessage(`Checkout opened in a new tab. Payment for ${plan} is pending activation.`);
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

  const handleDownloadInvoice = (invoiceId: string) => {
    setDownloadMessage(`${invoiceId} downloaded.`);
    setTimeout(() => {
      setDownloadMessage("");
    }, 2000);
  };

  return (
    <>
      <MotionSection>
        <p className="mb-3 text-xs font-bold uppercase tracking-[0.15em] text-[#b60055] sm:mb-4">Subscription Management</p>
        <h2 className="mb-3 text-3xl font-extrabold leading-tight tracking-tight text-[#203044] sm:mb-4 sm:text-4xl md:text-5xl md:leading-none">
          with surgical precision. <span className="text-[#68788f]">Choose your tier.</span>
        </h2>
        <p className="mb-2 text-sm font-semibold text-[#4d5d73]" aria-live="polite">
          Current plan: <span className="text-[#b60055]">{currentPlan}</span>
        </p>
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
                      Most Popular
                    </span>
                  </div>
                ) : null}

                <div>
                  <span
                    className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${
                      plan.featured ? "bg-[#b60055]/10 text-[#b60055]" : "bg-[#c9deff] text-[#4d5d73]"
                    }`}
                  >
                    {plan.badge}
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

                <MotionButton
                  type="button"
                  onClick={() => void handleSelectPlan(plan.name)}
                  disabled={isSubmitting}
                  className={`maas-touch-target mt-8 w-full rounded-xl px-5 py-3 font-bold transition disabled:opacity-70 sm:mt-10 md:mt-12 ${
                    isCurrent
                      ? "border-2 border-[#b60055] bg-white text-[#b60055]"
                      : plan.featured
                        ? "maas-enterprise-gradient text-white"
                        : plan.name === "Enterprise"
                          ? "bg-[#203044] text-[#f4f6ff]"
                          : "bg-[#d2e4ff] text-[#203044]"
                  }`}
                >
                  {isCurrent ? "Current Plan" : isPending ? "Pending Activation" : isSubmitting ? "Opening Checkout..." : plan.cta}
                </MotionButton>
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
              {[
                { id: "Invoice #MaaS-8821", date: "Oct 12, 2023", amount: "₱50.00", strong: true },
                { id: "Invoice #MaaS-7412", date: "Sep 12, 2023", amount: "₱50.00", strong: false },
              ].map((invoice, index) => (
                <motion.div
                  key={invoice.id}
                  className={`flex flex-col gap-3 rounded-xl bg-white p-4 sm:flex-row sm:items-center sm:justify-between ${invoice.strong ? "" : "opacity-70"}`}
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
                      <p className="text-sm font-bold">{invoice.id}</p>
                      <p className="text-[10px] font-medium uppercase text-[#68788f]">{invoice.date}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 sm:gap-6">
                    <p className="text-sm font-bold">{invoice.amount}</p>
                    <MotionButton type="button" className="maas-touch-target text-xs font-bold text-[#b60055] hover:underline" onClick={() => handleDownloadInvoice(invoice.id)}>
                      Download
                    </MotionButton>
                  </div>
                </motion.div>
              ))}
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
