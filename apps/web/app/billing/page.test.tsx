import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import BillingPage from "./page";

describe("Billing page", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders pricing tiers and upgrade action", () => {
    render(<BillingPage />);

    expect(screen.getByText(/subscription management/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upgrade Now" })).toBeInTheDocument();
  });

  it("updates current plan when selecting a tier", () => {
    render(<BillingPage />);

    expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Hobby");

    fireEvent.click(screen.getByRole("button", { name: "Upgrade Now" }));

    expect(screen.getByText(/Current plan:/i)).toHaveTextContent("Pro");
    expect(screen.getByRole("button", { name: "Current Plan" })).toBeInTheDocument();
  });
});
