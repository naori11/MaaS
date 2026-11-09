import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BillingPage from "./page";

vi.mock("../_lib/api/billing", () => ({
  getBillingStatus: vi.fn(),
  subscribeToPlan: vi.fn(),
  startProTrial: vi.fn(),
  cancelSubscription: vi.fn(),
  getPaymentHistory: vi.fn(),
  getReceipt: vi.fn(),
}));

const billingApi = await import("../_lib/api/billing");

describe("Billing page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(billingApi.getPaymentHistory).mockResolvedValue([]);
  });

  it("loads and renders current plan and v1 pricing catalog", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Pro",
      status: "active",
      expires_at: null,
      current_period_end: "2026-12-01T00:00:00Z",
      trial: { eligible: false, is_active: false, days_remaining: null, expires_at: null },
      usage: { used: 12, limit: null, unlimited: true, next_reset_at: "2026-11-05T00:00:00Z" },
      can_cancel: true,
    });

    render(<BillingPage />);

    expect(screen.getByText(/subscription management/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Pro");
    });

    expect(screen.getByText("₱0")).toBeInTheDocument();
    expect(screen.getByText("₱99")).toBeInTheDocument();
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("starts embedded checkout for Pro and keeps status pending activation", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Hobby",
      status: "active",
      expires_at: null,
      trial: { eligible: true, is_active: false, days_remaining: null, expires_at: null },
      usage: { used: 5, limit: 50, unlimited: false, next_reset_at: "2026-11-05T00:00:00Z" },
    });
    vi.mocked(billingApi.subscribeToPlan).mockResolvedValue({
      components_sdk_key: "xnd_public_test_components_sdk_key",
    });

    const createChannelPickerComponent = vi.fn(() => document.createElement("div"));
    const submit = vi.fn();
    const addEventListener = vi.fn();

    class MockXenditComponents {
      constructor(_: { componentsSdkKey: string }) {}

      createChannelPickerComponent = createChannelPickerComponent;
      submit = submit;
      addEventListener = addEventListener;
    }

    (window as Window & { Xendit?: { XenditComponents?: typeof MockXenditComponents } }).Xendit = {
      XenditComponents: MockXenditComponents,
    };

    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Hobby");
    });

    const proUpgradeButton = screen.getByRole("button", { name: "Upgrade to Pro" });
    fireEvent.click(proUpgradeButton);

    await waitFor(() => {
      expect(billingApi.subscribeToPlan).toHaveBeenCalledWith("Pro");
    });

    await waitFor(() => {
      expect(createChannelPickerComponent).toHaveBeenCalled();
    });

    expect(addEventListener).toHaveBeenCalledWith("session-complete", expect.any(Function));
    expect(addEventListener).toHaveBeenCalledWith("session-expired-or-canceled", expect.any(Function));
    expect(addEventListener).toHaveBeenCalledWith("fatal-error", expect.any(Function));
    expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Hobby");
    expect(screen.getByRole("status")).toHaveTextContent("Complete your embedded checkout to activate Pro.");
  });

  it("starts 7-day Pro preview when Try Pro free is selected", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Hobby",
      status: "active",
      expires_at: null,
      trial: { eligible: true, is_active: false, days_remaining: null, expires_at: null },
      usage: { used: 0, limit: 50, unlimited: false, next_reset_at: "2026-11-05T00:00:00Z" },
    });
    vi.mocked(billingApi.startProTrial).mockResolvedValue({
      status: "active",
      expires_at: "2026-11-11T00:00:00Z",
      days_remaining: 7,
    });

    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Try Pro free/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Try Pro free/i }));

    await waitFor(() => {
      expect(billingApi.startProTrial).toHaveBeenCalled();
    });
  });

  it("shows pending payment status from backend and allows resuming", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Pro",
      status: "pending_payment",
      expires_at: null,
    });
    vi.mocked(billingApi.subscribeToPlan).mockResolvedValue({
      components_sdk_key: "xnd_public_resume_components_sdk_key",
    });

    const createChannelPickerComponent = vi.fn(() => document.createElement("div"));
    const addEventListener = vi.fn();

    class MockXenditComponents {
      constructor(_: { componentsSdkKey: string }) {}

      createChannelPickerComponent = createChannelPickerComponent;
      submit = vi.fn();
      addEventListener = addEventListener;
    }

    (window as Window & { Xendit?: { XenditComponents?: typeof MockXenditComponents } }).Xendit = {
      XenditComponents: MockXenditComponents,
    };

    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Pro");
    });

    expect(screen.getByText(/Pending activation: Pro/i)).toBeInTheDocument();

    const resumeButton = await screen.findByRole("button", { name: "Resume Payment" });
    fireEvent.click(resumeButton);

    await waitFor(() => {
      expect(billingApi.subscribeToPlan).toHaveBeenCalledWith("Pro");
    });

    await waitFor(() => {
      expect(createChannelPickerComponent).toHaveBeenCalled();
    });

    expect(addEventListener).toHaveBeenCalledWith("session-complete", expect.any(Function));
    expect(addEventListener).toHaveBeenCalledWith("session-expired-or-canceled", expect.any(Function));
    expect(addEventListener).toHaveBeenCalledWith("fatal-error", expect.any(Function));
  });

  it("shows api error when status loading fails", async () => {
    vi.mocked(billingApi.getBillingStatus).mockRejectedValue(new Error("Gateway unavailable"));

    render(<BillingPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Gateway unavailable");
  });
});
