import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPage from "./page";

const ledgerItems = [
  {
    request_id: "req-1",
    operation_type: "addition",
    operand_a: 12,
    operand_b: 3,
    result: 15,
    math_transaction_id: "txn-ledger-1",
    created_at: "2026-04-10T12:00:00Z",
  },
];

describe("History page", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = "maas_auth_token=test-token; path=/";
    document.cookie = "maas_auth_token_type=bearer; path=/";
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      value: vi.fn(),
    });
    Object.defineProperty(globalThis, "fetch", {
      writable: true,
      value: vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ items: ledgerItems }),
      }),
    });
    HTMLAnchorElement.prototype.click = vi.fn();
  });

  it("renders history heading, key controls, and API-fed rows", async () => {
    render(<HistoryPage />);

    expect(screen.getByText(/enterprise logs/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export csv/i })).toBeInTheDocument();
    const renderedIds = await screen.findAllByText("txn-ledger-1");
    expect(renderedIds.length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.queryByText("#TX-94281-MA")).not.toBeInTheDocument();
    });

    expect(globalThis.fetch).toHaveBeenCalledWith("http://localhost:4000/api/v1/ledger/transactions?limit=100", {
      method: "GET",
      credentials: "include",
      headers: { Authorization: "Bearer test-token" },
    });
  });

  it("cycles filter modes", () => {
    render(<HistoryPage />);

    const filterButton = screen.getByRole("button", { name: /filter view/i });

    fireEvent.click(filterButton);
    expect(screen.getByRole("button", { name: /filter view: success/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /filter view: success/i }));
    expect(screen.getByRole("button", { name: /filter view: errors/i })).toBeInTheDocument();
  });

  it("exports filtered rows to csv", () => {
    render(<HistoryPage />);

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });
});
