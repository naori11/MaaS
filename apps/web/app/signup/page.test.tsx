import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SignupPage from "./page";

const { push, refresh, setAuthSession, fetchMock, nextValue } = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  setAuthSession: vi.fn(),
  fetchMock: vi.fn(),
  nextValue: { value: null as string | null },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
  }),
  useSearchParams: () => ({
    get: () => nextValue.value,
  }),
}));

vi.mock("../_lib/mock-auth", async () => {
  const actual = await vi.importActual<typeof import("../_lib/mock-auth")>("../_lib/mock-auth");

  return {
    ...actual,
    setAuthSession,
  };
});

describe("Signup page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nextValue.value = null;
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders account provisioning form", () => {
    render(<SignupPage />);

    expect(screen.getByRole("heading", { name: "Provision Account" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Provision Account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Node Identity")).toBeInTheDocument();
  });

  it("registers then logs in and navigates to calculator", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-1", email: "euler@maas.dev" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "jwt-token",
            token_type: "bearer",
            expires_in: 3600,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Full Name"), { target: { value: "Euler" } });
    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await waitFor(() => {
      expect(setAuthSession).toHaveBeenCalledWith({
        accessToken: "jwt-token",
        tokenType: "bearer",
        expiresInSeconds: 3600,
      });
      expect(push).toHaveBeenCalledWith("/calculator/focused");
      expect(refresh).toHaveBeenCalled();
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:4000/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:4000/api/v1/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows validation error when required fields are empty", () => {
    render(<SignupPage />);

    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Node Identity and Access Cipher are required.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("allows empty full name and still submits", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-1", email: "euler@maas.dev" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "jwt-token",
            token_type: "bearer",
            expires_in: 3600,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/calculator/focused");
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:4000/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows API failure message and stays on form", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { message: "Gateway unavailable" } }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Gateway unavailable");
    });

    expect(push).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("redirects to login when auto-login fails after register", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-1", email: "euler@maas.dev" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { message: "Invalid credentials" } }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      );

    render(<SignupPage />);

    fireEvent.change(screen.getByLabelText("Full Name"), { target: { value: "Euler" } });
    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "euler@maas.dev" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Provision Account" }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/login?next=%2Fcalculator%2Ffocused");
      expect(refresh).toHaveBeenCalled();
    });

    expect(setAuthSession).not.toHaveBeenCalled();
  });
});