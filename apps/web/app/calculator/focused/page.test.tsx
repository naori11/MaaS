import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CalculatorFocusedPage from "./page";

const { fetchMock, push, refresh, getAuthTokenFromBrowserSession, getAuthTokenTypeFromBrowserSession, clearAuthSession } = vi.hoisted(
  () => ({
    fetchMock: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    getAuthTokenFromBrowserSession: vi.fn(() => "jwt-token"),
    getAuthTokenTypeFromBrowserSession: vi.fn(() => "Bearer"),
    clearAuthSession: vi.fn(),
  }),
);

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
  }),
}));

vi.mock("../../_lib/mock-auth", async () => {
  const actual = await vi.importActual<typeof import("../../_lib/mock-auth")>("../../_lib/mock-auth");

  return {
    ...actual,
    getAuthTokenFromBrowserSession,
    getAuthTokenTypeFromBrowserSession,
    clearAuthSession,
  };
});

const makeSuccessResponse = (result: number, operation: "addition" | "subtraction" | "multiplication" | "division") =>
  new Response(
    JSON.stringify({
      operation,
      result,
      transaction_id: "tx-123",
      timestamp: "2026-04-11T00:00:00.000Z",
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

const pressKeys = (keys: string[]) => {
  for (const key of keys) {
    fireEvent.click(screen.getByRole("button", { name: key }));
  }
};

describe("Calculator focused page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", fetchMock);
    getAuthTokenFromBrowserSession.mockReturnValue("jwt-token");
    getAuthTokenTypeFromBrowserSession.mockReturnValue("Bearer");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders calculator display and primary controls", () => {
    render(<CalculatorFocusedPage />);

    expect(screen.getByText("Current Expression")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "=" })).toBeInTheDocument();
    expect(screen.getByLabelText("Calculator result")).toHaveTextContent("0");
  });

  it.each([
    {
      sequence: ["8", "+", "2", "="],
      endpoint: "http://localhost:4000/api/v1/calculate/add",
      result: 10,
      operation: "addition" as const,
      operandA: 8,
      operandB: 2,
    },
    {
      sequence: ["9", "−", "4", "="],
      endpoint: "http://localhost:4000/api/v1/calculate/subtract",
      result: 5,
      operation: "subtraction" as const,
      operandA: 9,
      operandB: 4,
    },
    {
      sequence: ["7", "×", "3", "="],
      endpoint: "http://localhost:4000/api/v1/calculate/multiply",
      result: 21,
      operation: "multiplication" as const,
      operandA: 7,
      operandB: 3,
    },
    {
      sequence: ["8", "÷", "2", "="],
      endpoint: "http://localhost:4000/api/v1/calculate/divide",
      result: 4,
      operation: "division" as const,
      operandA: 8,
      operandB: 2,
    },
  ])("maps operator to endpoint ($endpoint)", async ({ sequence, endpoint, result, operation, operandA, operandB }) => {
    fetchMock.mockResolvedValueOnce(makeSuccessResponse(result, operation));

    render(<CalculatorFocusedPage />);
    pressKeys(sequence);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(screen.getByLabelText("Calculator result")).toHaveTextContent(String(result));
    });

    expect(fetchMock).toHaveBeenCalledWith(
      endpoint,
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer jwt-token",
        },
        body: JSON.stringify({ operand_a: operandA, operand_b: operandB }),
      }),
    );
  });

  it("handles divide-by-zero locally without gateway call", () => {
    render(<CalculatorFocusedPage />);

    pressKeys(["9", "÷", "0", "="]);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Cannot divide by zero.");
    expect(screen.getByLabelText("Calculator result")).toHaveTextContent("0");
  });

  it("renders gateway errors in calculator-safe state", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Gateway unavailable" }), {
        status: 502,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    render(<CalculatorFocusedPage />);

    pressKeys(["8", "×", "2", "="]);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Gateway unavailable");
      expect(screen.getByLabelText("Calculator result")).toHaveTextContent("0");
    });
  });

  it("redirects to login when token is missing", async () => {
    getAuthTokenFromBrowserSession.mockReturnValueOnce(null);

    render(<CalculatorFocusedPage />);

    pressKeys(["8", "×", "2", "="]);

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/login?next=%2Fcalculator%2Ffocused");
      expect(refresh).toHaveBeenCalled();
    });

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears session and redirects to login on 401", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { message: "Invalid credentials" } }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    render(<CalculatorFocusedPage />);

    pressKeys(["8", "×", "2", "="]);

    await waitFor(() => {
      expect(clearAuthSession).toHaveBeenCalled();
      expect(push).toHaveBeenCalledWith("/login?next=%2Fcalculator%2Ffocused");
      expect(refresh).toHaveBeenCalled();
    });
  });
});
