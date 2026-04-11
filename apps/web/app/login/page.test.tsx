import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

const { push, refresh, setAuthSession, fetchMock, nextValue } = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn(),
  setAuthSession: vi.fn(),
  fetchMock: vi.fn(),
  nextValue: { value: "/history" as string | null },
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

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nextValue.value = "/history";
    vi.stubGlobal("fetch", fetchMock);
  });

  it("renders session initiation form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByLabelText("Node Identity")).toBeInTheDocument();
    expect(screen.getByLabelText("Access Cipher")).toBeInTheDocument();
  });

  it("submits credentials, stores session, and navigates", async () => {
    fetchMock.mockResolvedValueOnce(
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

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    await waitFor(() => {
      expect(setAuthSession).toHaveBeenCalledWith({
        accessToken: "jwt-token",
        tokenType: "bearer",
        expiresInSeconds: 3600,
      });
      expect(push).toHaveBeenCalledWith("/history");
      expect(refresh).toHaveBeenCalled();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:4000/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("shows validation error when fields are empty", () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Node Identity and Access Cipher are required.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows invalid credential error from gateway", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { message: "Invalid credentials" },
        }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials");
    });

    expect(setAuthSession).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("shows gateway unreachable error", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network down"));

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Unable to reach authentication gateway.");
    });

    expect(setAuthSession).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });
});