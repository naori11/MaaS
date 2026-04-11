import type { LedgerTransaction } from "../api/ledger";
import type { HistoryRow } from "../mock-history";

const operationLabels: Record<LedgerTransaction["operation_type"], HistoryRow["operation"]> = {
  addition: "ADDITION",
  subtraction: "SUBTRACTION",
  multiplication: "MULTIPLICATION",
  division: "DIVISION",
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 8,
  }).format(value);
}

function formatTimestamp(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const datePart = date.toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });

  const timePart = date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return `${datePart} · ${timePart}`;
}

export function toHistoryRows(items: LedgerTransaction[]): HistoryRow[] {
  return items.map((item) => ({
    id: item.math_transaction_id,
    inputA: formatNumber(item.operand_a),
    operation: operationLabels[item.operation_type],
    inputB: formatNumber(item.operand_b),
    result: formatNumber(item.result),
    timestamp: formatTimestamp(item.created_at),
    status: "Success",
    error: false,
  }));
}
