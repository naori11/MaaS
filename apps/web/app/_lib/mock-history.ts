export type HistoryRow = {
  id: string;
  inputA: string;
  operation: string;
  inputB: string;
  result: string;
  timestamp: string;
  status: string;
  error: boolean;
};

export type HistoryOperation = "MULTIPLICATION" | "DIVISION" | "SUBTRACTION" | "ADDITION";

const HISTORY_STORAGE_KEY = "maas_mock_history";

const seedHistoryRows: HistoryRow[] = [
  {
    id: "#TX-94281-MA",
    inputA: "1,245.00",
    operation: "MULTIPLICATION",
    inputB: "0.85",
    result: "1,058.25",
    timestamp: "Oct 24, 2023 · 14:22:10",
    status: "Success",
    error: false,
  },
  {
    id: "#TX-94279-MA",
    inputA: "85.00",
    operation: "DIVISION",
    inputB: "0",
    result: "ERR:UNDEFINED",
    timestamp: "Oct 24, 2023 · 12:45:01",
    status: "Division by Zero",
    error: true,
  },
  {
    id: "#TX-94278-MA",
    inputA: "55,200.00",
    operation: "SUBTRACTION",
    inputB: "12,400.00",
    result: "42,800.00",
    timestamp: "Oct 24, 2023 · 10:15:33",
    status: "Success",
    error: false,
  },
  {
    id: "#TX-94277-MA",
    inputA: "12.00",
    operation: "ADDITION",
    inputB: "3",
    result: "15.00",
    timestamp: "Oct 23, 2023 · 22:50:44",
    status: "Success",
    error: false,
  },
];

const operationLabels: Record<"+" | "−" | "×" | "÷", HistoryOperation> = {
  "+": "ADDITION",
  "−": "SUBTRACTION",
  "×": "MULTIPLICATION",
  "÷": "DIVISION",
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 8,
  }).format(value);
}

function formatTimestamp(date: Date) {
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

function generateTransactionId() {
  const random = Math.floor(10000 + Math.random() * 90000);
  return `#TX-${random}-MA`;
}

export function getSeedHistoryRows() {
  return [...seedHistoryRows];
}

export function loadHistoryRows() {
  if (typeof window === "undefined") {
    return getSeedHistoryRows();
  }

  const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
  if (!raw) {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(seedHistoryRows));
    return getSeedHistoryRows();
  }

  try {
    const parsed = JSON.parse(raw) as HistoryRow[];
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return getSeedHistoryRows();
    }
    return parsed;
  } catch {
    return getSeedHistoryRows();
  }
}

export function saveHistoryRows(rows: HistoryRow[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(rows));
}

export function appendHistoryCalculation(inputA: number, operator: "+" | "−" | "×" | "÷", inputB: number, result: number | null) {
  const rows = loadHistoryRows();
  const error = result === null;

  const nextRow: HistoryRow = {
    id: generateTransactionId(),
    inputA: formatNumber(inputA),
    operation: operationLabels[operator],
    inputB: formatNumber(inputB),
    result: error ? "ERR:UNDEFINED" : formatNumber(result),
    timestamp: formatTimestamp(new Date()),
    status: error ? "Division by Zero" : "Success",
    error,
  };

  const nextRows = [nextRow, ...rows].slice(0, 200);
  saveHistoryRows(nextRows);

  return nextRows;
}

export function toHistoryCsv(rows: HistoryRow[]) {
  const header = ["Transaction ID", "Input A", "Operation", "Input B", "Result", "Timestamp", "Status"];
  const body = rows.map((row) => [row.id, row.inputA, row.operation, row.inputB, row.result, row.timestamp, row.status]);
  return [header, ...body]
    .map((line) =>
      line
        .map((value) => `"${String(value).replaceAll('"', '""')}"`)
        .join(","),
    )
    .join("\n");
}
