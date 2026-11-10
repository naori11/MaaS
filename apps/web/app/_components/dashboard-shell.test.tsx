import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardShell } from "./dashboard-shell";
import { getBillingStatus } from "../_lib/api/billing";

vi.mock("../_lib/api/billing", () => ({
  getBillingStatus: vi.fn().mockResolvedValue({
    plan_name: "Hobby",
    status: "active",
    usage: { used: 12, limit: 50, unlimited: false, next_reset_at: "2026-11-06T00:00:00Z" },
    trial: { eligible: true, is_active: false, days_remaining: null, expires_at: null },
  }),
}));

describe("DashboardShell", () => {
  it("keeps sidebar and mobile nav without duplicate top tab links", () => {
    const { container } = render(
      <DashboardShell activeTab="calculator" title="Calculator View">
        <div>content</div>
      </DashboardShell>,
    );

    expect(container.querySelectorAll('a[href="/calculator/focused"]')).toHaveLength(2);
    expect(container.querySelectorAll('a[href="/history"]')).toHaveLength(2);
    expect(container.querySelectorAll('a[href="/billing"]')).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /^calculator$/i })).not.toBeInTheDocument();
  });

  it("shows daily usage in the mobile layout and the desktop sidebar", async () => {
    const { container } = render(
      <DashboardShell activeTab="calculator" title="Calculator View">
        <div>content</div>
      </DashboardShell>,
    );

    expect(await screen.findAllByText("12 / 50 calcs")).toHaveLength(1);
    expect(screen.getByText("12 / 50 calculations")).toBeInTheDocument();
    expect(container.querySelector('[aria-label="Daily calculation usage"]')).toBeInTheDocument();
  });

  it("refreshes usage after a successful calculation event", async () => {
    vi.mocked(getBillingStatus).mockClear();
    render(
      <DashboardShell activeTab="calculator" title="Calculator View">
        <div>content</div>
      </DashboardShell>,
    );
    await screen.findByText("12 / 50 calculations");
    expect(getBillingStatus).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new Event("maas:usage-updated"));

    await vi.waitFor(() => expect(getBillingStatus).toHaveBeenCalledTimes(2));
  });
});
