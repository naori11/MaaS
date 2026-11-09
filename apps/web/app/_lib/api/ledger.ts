import { getAuthTokenFromBrowserSession } from "../auth/session";
import { handleUnauthorized } from "./client";

import { getGatewayBaseUrl } from "./gateway-url";
const GATEWAY_BASE_URL = getGatewayBaseUrl();
const LEDGER_TRANSACTIONS_PATH = "/api/v1/ledger/transactions";

export type LedgerTransaction = {
  request_id: string;
  operation_type: "addition" | "subtraction" | "multiplication" | "division";
  operand_a: number;
  operand_b: number;
  result: number;
  math_transaction_id: string;
  created_at: string;
};

export type LedgerTransactionsResponse = {
  items: LedgerTransaction[];
  next_cursor: string | null;
};

export async function fetchLedgerTransactions(limit = 10, cursor?: string | null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  const token = getAuthTokenFromBrowserSession();
  const authorization = token ? `Bearer ${token}` : null;
  const headers = authorization ? { Authorization: authorization } : undefined;

  const response = await fetch(`${getGatewayBaseUrl()}${LEDGER_TRANSACTIONS_PATH}?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  handleUnauthorized(response, Boolean(token));

  if (!response.ok) {
    throw new Error("Failed to load ledger transactions");
  }

  return (await response.json()) as LedgerTransactionsResponse;
}
