"use client";

import { useEffect, useState } from "react";
import { DashboardShell } from "../_components/dashboard-shell";
import { getDefaultBillingState, loadBillingState, saveBillingState, type BillingPlanName } from "../_lib/mock-billing";

type Plan = {
  name: BillingPlanName;
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
    name: "Hobby" as const,
    badge: "Sandbox",
    price: "$0",
    period: "/month",
    cta: "Start Computing",
    featured: false,
    features: ["10 additions/day. No subtraction.", "Public calculation history", "Multi-threaded solving"],
    unavailable: [2],
  },
  {
    name: "Pro" as const,
    badge: "Growth",
    price: "$29",
    period: "/month",
    cta: "Upgrade Now",
    featured: true,
    features: ["Unlimited basic math.", "Private result logs", "Priority equation queuing", "Algebraic support"],
    unavailable: [],
  },
  {
    name: "Enterprise" as const,
    badge: "Scale",
    price: "Custom",
    period: "",
    cta: "Contact Sales",
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
  const [currentPlan, setCurrentPlan] = useState<BillingPlanName>("Hobby");
  const [paymentMethod, setPaymentMethod] = useState(getDefaultBillingState().paymentMethod);
  const [showPaymentOptions, setShowPaymentOptions] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState("");

  useEffect(() => {
    const state = loadBillingState();
    setCurrentPlan(state.currentPlan);
    setPaymentMethod(state.paymentMethod);
  }, []);

  const updateState = (nextPlan: BillingPlanName, nextMethod: string) => {
    saveBillingState({ currentPlan: nextPlan, paymentMethod: nextMethod });
    setCurrentPlan(nextPlan);
    setPaymentMethod(nextMethod);
  };

  const handleSelectPlan = (plan: BillingPlanName) => {
    updateState(plan, paymentMethod);
  };

  const handleSelectPaymentMethod = (method: string) => {
    updateState(currentPlan, method);
    setShowPaymentOptions(false);
  };

  const handleDownloadInvoice = (invoiceId: string) => {
    setDownloadMessage(`${invoiceId} downloaded.`);
    setTimeout(() => {
      setDownloadMessage("");
    }, 2000);
  };

  return (
    <DashboardShell
      activeTab="billing"
      title="Scale your logic"
      subtitle="Transparent pricing designed for everyone from hobbyist calculators to enterprise-grade arithmetic clusters."
    >
      <p className="mb-4 text-xs font-bold uppercase tracking-[0.15em] text-[#b60055]">Subscription Management</p>
      <h2 className="mb-4 text-5xl font-extrabold leading-none tracking-tight text-[#203044]">
        with surgical precision. <span className="text-[#68788f]">Choose your tier.</span>
      </h2>
      <p className="mb-14 text-sm font-semibold text-[#4d5d73]" aria-live="polite">
        Current plan: <span className="text-[#b60055]">{currentPlan}</span>
      </p>

      <section className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.name;

          return (
            <article
              key={plan.name}
              className={`flex flex-col justify-between rounded-3xl p-8 ${
                plan.featured
                  ? "relative overflow-hidden border-2 border-[#b60055]/10 bg-white shadow-[0px_20px_40px_rgba(32,48,68,0.06)]"
                  : "bg-[#eaf1ff]"
              }`}
            >
              {plan.featured ? (
                <div className="absolute right-0 top-0 p-4">
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
                <h3 className="mt-4 text-3xl font-bold">{plan.name}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-4xl font-black">{plan.price}</span>
                  {plan.period ? <span className="text-sm text-[#4d5d73]">{plan.period}</span> : null}
                </div>

                <ul className="mt-8 space-y-6">
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

              <button
                type="button"
                onClick={() => handleSelectPlan(plan.name)}
                className={`mt-12 w-full rounded-xl px-6 py-4 font-bold transition ${
                  isCurrent
                    ? "border-2 border-[#b60055] bg-white text-[#b60055]"
                    : plan.featured
                      ? "maas-enterprise-gradient text-white"
                      : plan.name === "Enterprise"
                        ? "bg-[#203044] text-[#f4f6ff]"
                        : "bg-[#d2e4ff] text-[#203044]"
                }`}
              >
                {isCurrent ? "Current Plan" : plan.cta}
              </button>
            </article>
          );
        })}
      </section>

      <section className="mt-24 grid grid-cols-1 items-center gap-12 md:grid-cols-12">
        <article className="rounded-3xl border border-[#9eaec7]/10 bg-[#eaf1ff]/50 p-10 md:col-span-7">
          <h4 className="mb-6 text-2xl font-bold">Payment History</h4>
          {downloadMessage ? (
            <p className="mb-4 rounded-lg border border-[#b60055]/15 bg-[#b60055]/5 px-3 py-2 text-xs font-semibold text-[#b60055]" role="status">
              {downloadMessage}
            </p>
          ) : null}
          <div className="space-y-4">
            {[
              { id: "Invoice #MaaS-8821", date: "Oct 12, 2023", amount: "$29.00", strong: true },
              { id: "Invoice #MaaS-7412", date: "Sep 12, 2023", amount: "$29.00", strong: false },
            ].map((invoice) => (
              <div
                key={invoice.id}
                className={`flex items-center justify-between rounded-xl bg-white p-4 ${invoice.strong ? "" : "opacity-70"}`}
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#c8d8f3]">
                    <span className="material-symbols-outlined text-[#3c4c61]">receipt</span>
                  </div>
                  <div>
                    <p className="text-sm font-bold">{invoice.id}</p>
                    <p className="text-[10px] font-medium uppercase text-[#68788f]">{invoice.date}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <p className="text-sm font-bold">{invoice.amount}</p>
                  <button type="button" className="text-xs font-bold text-[#b60055] hover:underline" onClick={() => handleDownloadInvoice(invoice.id)}>
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>

        <div className="space-y-8 md:col-span-5">
          <article className="rounded-3xl border border-[#9eaec7]/10 bg-white p-8 shadow-sm">
            <div className="mb-6 flex items-center gap-4">
              <div className="maas-enterprise-gradient flex h-12 w-12 items-center justify-center rounded-xl text-white">
                <span className="material-symbols-outlined">credit_score</span>
              </div>
              <div>
                <h4 className="font-bold">Primary Method</h4>
                <p className="text-sm text-[#4d5d73]">{paymentMethod}</p>
              </div>
            </div>
            <button
              type="button"
              className="w-full rounded-lg border-2 border-[#9eaec7]/20 py-3 text-sm font-bold"
              onClick={() => setShowPaymentOptions((value) => !value)}
            >
              {showPaymentOptions ? "Hide Payment Methods" : "Update Payment Method"}
            </button>
            {showPaymentOptions ? (
              <div className="mt-4 space-y-2">
                {paymentMethods.map((method) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => handleSelectPaymentMethod(method)}
                    className="w-full rounded-lg bg-[#eaf1ff] px-3 py-2 text-left text-xs font-semibold text-[#203044]"
                  >
                    {method}
                  </button>
                ))}
              </div>
            ) : null}
          </article>

          <article className="rounded-3xl border border-[#b60055]/10 bg-[#b60055]/5 p-8">
            <h4 className="mb-2 font-bold">Need a custom math quota?</h4>
            <p className="mb-6 text-sm text-[#4d5d73]">
              Our sales team can tailor a plan that fits your exact computational throughput needs.
            </p>
            <a href="/signup" className="group flex items-center gap-2 text-sm font-bold text-[#b60055]">
              Talk to an expert
              <span className="material-symbols-outlined text-sm transition group-hover:translate-x-1">arrow_forward</span>
            </a>
          </article>
        </div>
      </section>
    </DashboardShell>
  );
}
