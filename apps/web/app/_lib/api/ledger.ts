const GATEWAY_BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:4000").replace(/\/$/, "");
const LEDGER_TRANSACTIONS_PATH = "/api/v1/ledger/transactions";
const AUTH_TOKEN_COOKIE = "maas_auth_token";
const AUTH_TOKEN_TYPE_COOKIE = "maas_auth_token_type";

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
};

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const entry = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`));

  if (!entry) {
    return null;
  }

  return decodeURIComponent(entry.slice(name.length + 1));
}

function getAuthorizationHeaderValue(): string | null {
  const token = readCookie(AUTH_TOKEN_COOKIE);

  if (!token) {
    return null;
  }

  const tokenType = readCookie(AUTH_TOKEN_TYPE_COOKIE) ?? "bearer";
  const normalizedType = tokenType.toLowerCase() === "bearer" ? "Bearer" : tokenType;

  return `${normalizedType} ${token}`;
}

export async function fetchLedgerTransactions(limit: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  const authorization = getAuthorizationHeaderValue();
  const headers = authorization ? { Authorization: authorization } : undefined;

  const response = await fetch(`${GATEWAY_BASE_URL}${LEDGER_TRANSACTIONS_PATH}?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    throw new Error("Failed to load ledger transactions");
  }

  return (await response.json()) as LedgerTransactionsResponse;
}
