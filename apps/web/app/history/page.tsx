"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { MotionButton, MotionCard } from "../_components/motion/motion-primitives";
import { fetchLedgerTransactions } from "../_lib/api/ledger";
import { toHistoryRows } from "../_lib/history/adapter";
import { MOTION_DURATION, MOTION_EASE } from "../_lib/motion/tokens";
import { formatHistoryCalculation, toHistoryCsv, type HistoryRow } from "../_lib/mock-history";
import { getAuthTokenFromBrowserSession } from "../_lib/auth/session";

type FilterMode = "all" | "success" | "errors";

const PAGE_SIZE = 10;
import { getGatewayBaseUrl } from "../_lib/api/gateway-url";
const GATEWAY_BASE_URL = getGatewayBaseUrl();

export default function HistoryPage() {
  const shouldReduceMotion = useReducedMotion();
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [pageCursors, setPageCursors] = useState<(string | null)[]>([null]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const currentCursor = pageCursors[pageCursors.length - 1] ?? null;

  useEffect(() => {
    let isActive = true;

    void (async () => {
      try {
        setIsLoading(true);
        const response = await fetchLedgerTransactions(PAGE_SIZE, currentCursor);
        if (!isActive) {
          return;
        }
        setRows(toHistoryRows(response.items));
        setNextCursor(response.next_cursor ?? null);
      } catch {
        if (!isActive) {
          return;
        }
        setRows([]);
        setNextCursor(null);
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      isActive = false;
    };
  }, [currentCursor]);

  const filteredRows = useMemo(() => {
    if (filter === "success") {
      return rows.filter((row) => !row.error);
    }

    if (filter === "errors") {
      return rows.filter((row) => row.error);
    }

    return rows;
  }, [filter, rows]);

  const handleFilterCycle = () => {
    setFilter((current) => {
      if (current === "all") {
        return "success";
      }

      if (current === "success") {
        return "errors";
      }

      return "all";
    });
  };

  const exportCsv = async () => {
    setIsExporting(true);
    setExportError("");

    try {
      const token = getAuthTokenFromBrowserSession();
      try {
        const res = await fetch(`${getGatewayBaseUrl()}/api/v1/ledger/export`, {
          method: "GET",
          credentials: "include",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (res.status === 403) {
          setExportError("CSV export is only available on the Pro plan.");
          return;
        }

        if (res.ok && typeof res.blob === "function") {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute("download", "math-history.csv");
          document.body.append(link);
          link.click();
          link.remove();
          URL.revokeObjectURL(url);
          return;
        }
      } catch {
        // Fall back to client generation if standalone endpoint not reachable
      }

      const allRows: HistoryRow[] = [];
      let cursor: string | null = null;
      do {
        const response = await fetchLedgerTransactions(PAGE_SIZE, cursor);
        allRows.push(...toHistoryRows(response.items));
        cursor = response.next_cursor;
      } while (cursor);

      const exportRows = allRows.filter((row) => {
        if (filter === "success") return !row.error;
        if (filter === "errors") return row.error;
        return true;
      });
      const csv = toHistoryCsv(exportRows);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.setAttribute("download", "math-history.csv");
      document.body.append(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "CSV export failed.");
    } finally {
      setIsExporting(false);
    }
  };

  const goToNextPage = () => {
    if (nextCursor) {
      setPageCursors((current) => [...current, nextCursor]);
    }
  };

  const goToPreviousPage = () => {
    setPageCursors((current) => (current.length > 1 ? current.slice(0, -1) : current));
  };

  const filterLabel =
    filter === "all" ? "Filter View: All" : filter === "success" ? "Filter View: Success" : "Filter View: Errors";

  return (
    <>
      <div className="flex flex-col gap-4 pb-8 sm:flex-row sm:items-center sm:justify-between sm:pb-10">
        <div className="max-w-2xl">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.1em] text-[#b60055]">Enterprise Logs</p>
          <p className="text-xs text-[#4d5d73]">
            Hobby plan includes 7 days of calculation history. Upgrade to Pro for full private synced history and CSV export.
          </p>
        </div>
        <div className="grid w-full grid-cols-1 gap-3 sm:w-auto sm:grid-cols-2 sm:gap-4">
          <MotionButton
            type="button"
            onClick={handleFilterCycle}
            className="maas-touch-target flex items-center justify-center gap-2 rounded-lg bg-[#dce9ff] px-4 py-3 text-xs font-semibold sm:justify-start sm:px-5 sm:text-sm"
          >
            <span className="material-symbols-outlined text-sm">filter_list</span>
            <span className="truncate">{filterLabel}</span>
          </MotionButton>
          <MotionButton
            type="button"
            onClick={exportCsv}
            disabled={isLoading || isExporting}
            className="maas-enterprise-gradient maas-touch-target flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-xs font-bold text-white shadow-lg shadow-[#b60055]/20 sm:px-5 sm:text-sm"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            {isExporting ? "Preparing CSV…" : "Export CSV"}
          </MotionButton>
        </div>
      </div>

      {exportError ? (
        <div role="alert" className="mb-6 flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-semibold text-rose-800">
          <span>{exportError}</span>
          <Link href="/billing" className="underline hover:text-rose-900">
            Upgrade to Pro &rarr;
          </Link>
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl bg-[#eaf1ff] sm:rounded-3xl">
        <div className="md:hidden">
          {filteredRows.length > 0 ? (
            <div className="space-y-3 p-3 sm:p-4">
              {filteredRows.map((row, index) => (
                <motion.article
                  key={row.id}
                  className="rounded-xl bg-white p-4 shadow-sm"
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: shouldReduceMotion ? MOTION_DURATION.fast : MOTION_DURATION.base,
                    ease: MOTION_EASE.standard,
                    delay: shouldReduceMotion ? 0 : index * 0.03,
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-[#203044]">{formatHistoryCalculation(row)}</p>
                      <p className="text-[10px] uppercase text-[#68788f]">{row.timestamp}</p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] ${
                        row.error ? "bg-[#ff8da6]/20 text-[#b60055]" : "bg-[#c9deff] text-[#203044]"
                      }`}
                    >
                      {row.error ? "Error" : "Success"}
                    </span>
                  </div>
                  <div className="mt-3 flex items-baseline justify-between border-t border-[#9eaec7]/20 pt-3">
                    <span className="text-[10px] font-bold uppercase text-[#68788f]">Result</span>
                    <span className="text-sm font-black text-[#203044]">{row.result}</span>
                  </div>
                </motion.article>
              ))}
            </div>
          ) : (
            <p className="p-6 text-center text-xs font-medium text-[#4d5d73]">
              {isLoading ? "Loading calculation history…" : "No calculation transactions match this view."}
            </p>
          )}
        </div>

        <div className="hidden md:block">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-[#9eaec7]/20 text-[10px] font-bold uppercase tracking-[0.15em] text-[#4d5d73]">
                <th className="px-6 py-4">Date &amp; Time</th>
                <th className="px-6 py-4">Calculation</th>
                <th className="px-6 py-4">Result</th>
                <th className="px-6 py-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#9eaec7]/20 font-mono text-xs">
              {filteredRows.length > 0 ? (
                filteredRows.map((row) => (
                  <tr key={row.id} className="transition-colors hover:bg-white/60">
                    <td className="px-6 py-4 font-sans text-xs text-[#4d5d73]">{row.timestamp}</td>
                    <td className="px-6 py-4 font-bold text-[#203044]">{formatHistoryCalculation(row)}</td>
                    <td className="px-6 py-4 font-bold text-[#203044]">{row.result}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] ${
                          row.error ? "bg-[#ff8da6]/20 text-[#b60055]" : "bg-[#c9deff] text-[#203044]"
                        }`}
                      >
                        {row.error ? "Error" : "Success"}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center font-sans text-xs font-medium text-[#4d5d73]">
                    {isLoading ? "Loading calculation history…" : "No calculation transactions match this view."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-3 border-t border-[#9eaec7]/20 bg-white/40 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="text-xs font-medium text-[#4d5d73]">
            Page {pageCursors.length} &bull; Showing up to {PAGE_SIZE} rows per page
          </p>
          <div className="flex items-center gap-2">
            <MotionButton
              type="button"
              onClick={goToPreviousPage}
              disabled={pageCursors.length <= 1 || isLoading}
              className="maas-touch-target rounded-lg border border-[#9eaec7]/20 bg-white px-3 py-1.5 text-xs font-semibold text-[#203044] disabled:opacity-40"
            >
              Previous
            </MotionButton>
            <MotionButton
              type="button"
              onClick={goToNextPage}
              disabled={!nextCursor || isLoading}
              className="maas-touch-target rounded-lg border border-[#9eaec7]/20 bg-white px-3 py-1.5 text-xs font-semibold text-[#203044] disabled:opacity-40"
            >
              Next
            </MotionButton>
          </div>
        </div>
      </section>
    </>
  );
}
