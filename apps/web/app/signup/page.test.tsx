import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SignupPage from "./page";

const push = vi.fn();
const refresh = vi.fn();
let nextValue: string | null = null;

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
  }),
  useSearchParams: () => ({
    get: () => nextValue,
  }),
}));

describe("Signup page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    nextValue = null;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders account provisioning form", () => {
    render(<SignupPage />);

    expect(screen.getByRole("heading", { name: "Provision Account" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Provision Account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Node Identity")).toBeInTheDocument();
  });

  it("submits and navigates to calculator by default", async () => {
    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Full Name"), { target: { value: "Euler" } });
    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(push).toHaveBeenCalledWith("/calculator/focused");
    expect(refresh).toHaveBeenCalled();
  });

  it("shows validation error when fields are empty", () => {
    render(<SignupPage />);

    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Full Name, Node Identity, and Access Cipher are required.");
  });
});
