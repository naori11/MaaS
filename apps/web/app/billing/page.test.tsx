import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BillingPage from "./page";

vi.mock("../_lib/api/billing", () => ({
  getBillingStatus: vi.fn(),
  subscribeToPlan: vi.fn(),
}));

const billingApi = await import("../_lib/api/billing");

describe("Billing page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  it("loads and renders current plan from billing status", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Standard",
      status: "active",
      expires_at: null,
    });

    render(<BillingPage />);

    expect(screen.getByText(/subscription management/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Pro");
    });

    expect(screen.getByText("₱0")).toBeInTheDocument();
    expect(screen.getByText("₱50")).toBeInTheDocument();
    expect(screen.getByText("₱250")).toBeInTheDocument();
  });

  it("starts checkout and keeps plan pending activation", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Free",
      status: "active",
      expires_at: null,
    });
    vi.mocked(billingApi.subscribeToPlan).mockResolvedValue({
      invoice_url: "https://billing.example/invoice/123",
    });

    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Hobby");
    });

    const [proUpgradeButton] = screen.getAllByRole("button", { name: "Upgrade Now" });
    fireEvent.click(proUpgradeButton);

    await waitFor(() => {
      expect(billingApi.subscribeToPlan).toHaveBeenCalledWith("Standard");
    });

    expect(window.open).toHaveBeenCalledWith("https://billing.example/invoice/123", "_blank", "noopener,noreferrer");
    expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Hobby");
    expect(screen.getByRole("status")).toHaveTextContent("Checkout opened in a new tab. Payment for Pro is pending activation.");
  });

  it("shows pending payment status from backend", async () => {
    vi.mocked(billingApi.getBillingStatus).mockResolvedValue({
      plan_name: "Premium",
      status: "pending_payment",
      expires_at: null,
    });

    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Enterprise");
    });

    expect(screen.getByText(/Pending activation: Enterprise/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Payment for Enterprise is pending. Complete checkout to activate your plan.");
  });

  it("shows api error when status loading fails", async () => {
    vi.mocked(billingApi.getBillingStatus).mockRejectedValue(new Error("Gateway unavailable"));

    render(<BillingPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Gateway unavailable");
  });
});
