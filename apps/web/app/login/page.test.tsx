import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";
import { loginWithPassword } from "../_lib/api/auth-login";
import { setAuthSession } from "../_lib/auth/session";

const push = vi.fn();
const refresh = vi.fn();
let nextValue: string | null = "/history";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
  }),
  useSearchParams: () => ({
    get: () => nextValue,
  }),
}));

vi.mock("../_lib/api/auth-login", () => ({
  loginWithPassword: vi.fn(),
}));

vi.mock("../_lib/auth/session", () => ({
  setAuthSession: vi.fn(),
}));

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nextValue = "/history";
  });

  it("renders session initiation form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByLabelText("Node Identity")).toBeInTheDocument();
    expect(screen.getByLabelText("Access Cipher")).toBeInTheDocument();
  });

  it("submits and navigates to next route", async () => {
    vi.mocked(loginWithPassword).mockResolvedValue({
      access_token: "jwt-token",
      token_type: "bearer",
      expires_in: 3600,
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    await waitFor(() => {
      expect(loginWithPassword).toHaveBeenCalledWith({
        email: "user@example.com",
        password: "secret123",
      });
    });

    expect(setAuthSession).toHaveBeenCalledWith({
      accessToken: "jwt-token",
      tokenType: "bearer",
      expiresInSeconds: 3600,
    });
    expect(push).toHaveBeenCalledWith("/history");
    expect(refresh).toHaveBeenCalled();
  });

  it("shows validation error when fields are empty", () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Node Identity and Access Cipher are required.");
    expect(loginWithPassword).not.toHaveBeenCalled();
  });

  it("shows gateway error message when login fails", async () => {
    vi.mocked(loginWithPassword).mockRejectedValue(new Error("Invalid credentials"));

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "wrongpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials");
    });

    expect(setAuthSession).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });
});
