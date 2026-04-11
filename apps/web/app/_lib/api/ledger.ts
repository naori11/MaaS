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
};

export async function fetchLedgerTransactions(limit: number) {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`${LEDGER_TRANSACTIONS_PATH}?${params.toString()}`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Failed to load ledger transactions");
  }

  return (await response.json()) as LedgerTransactionsResponse;
}
