import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SignupPage from "./page";
import { register } from "../_lib/api/auth-register";

const push = vi.fn();
const refresh = vi.fn();
let nextValue: string | null = null;

vi.mock("../_lib/api/auth-register", () => ({
  register: vi.fn(),
}));

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
    vi.mocked(register).mockResolvedValue({
      id: "user-1",
      email: "euler@maas.dev",
      created_at: "2026-01-01T00:00:00Z",
    });
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

    await act(async () => {
      await Promise.resolve();
    });

    expect(register).toHaveBeenCalledWith({
      email: "euler@maas.dev",
      password: "secret",
    });
    expect(push).toHaveBeenCalledWith("/calculator/focused");
    expect(refresh).toHaveBeenCalled();
  });
  it("shows validation error when required fields are empty", () => {
    render(<SignupPage />);

    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Node Identity and Access Cipher are required.");
  });

  it("allows empty full name and still submits", async () => {
    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(register).toHaveBeenCalledWith({
      email: "euler@maas.dev",
      password: "secret",
    });
    expect(push).toHaveBeenCalledWith("/calculator/focused");
  });

  it("shows API failure message and stays on form", async () => {
    vi.mocked(register).mockRejectedValueOnce(new Error("Gateway unavailable"));
    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Unable to provision account. Please try again.");
    expect(push).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });
});
