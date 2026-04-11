"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { MotionButton, MotionCard } from "../_components/motion/motion-primitives";
import { fetchLedgerTransactions } from "../_lib/api/ledger";
import { toHistoryRows } from "../_lib/history/adapter";
import { MOTION_DURATION, MOTION_EASE } from "../_lib/motion/tokens";
import { getSeedHistoryRows, toHistoryCsv, type HistoryRow } from "../_lib/mock-history";

type FilterMode = "all" | "success" | "errors";

const PAGE_SIZE = 6;

export default function HistoryPage() {
  const shouldReduceMotion = useReducedMotion();
  const [rows, setRows] = useState<HistoryRow[]>(getSeedHistoryRows());
  const [filter, setFilter] = useState<FilterMode>("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let isActive = true;

    void (async () => {
      try {
        const response = await fetchLedgerTransactions(100);
        if (!isActive) {
          return;
        }
        setRows(toHistoryRows(response.items));
      } catch {
        if (!isActive) {
          return;
        }
        setRows([]);
      }
    })();

    return () => {
      isActive = false;
    };
  }, []);

  const filteredRows = useMemo(() => {
    if (filter === "success") {
      return rows.filter((row) => !row.error);
    }

    if (filter === "errors") {
      return rows.filter((row) => row.error);
    }

    return rows;
  }, [filter, rows]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const pagedRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredRows.slice(start, start + PAGE_SIZE);
  }, [filteredRows, page]);

  const handleFilterCycle = () => {
    setPage(1);
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

  const exportCsv = () => {
    const csv = toHistoryCsv(filteredRows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.setAttribute("download", "maas-history.csv");
    document.body.append(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  };

  const filterLabel =
    filter === "all" ? "Filter View: All" : filter === "success" ? "Filter View: Success" : "Filter View: Errors";

  return (
    <>
      <div className="flex flex-col gap-4 pb-8 sm:flex-row sm:items-center sm:justify-between sm:pb-10">
        <div className="max-w-2xl">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.1em] text-[#b60055]">Enterprise Logs</p>
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
            className="maas-enterprise-gradient maas-touch-target flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-xs font-bold text-white shadow-lg shadow-[#b60055]/20 sm:px-5 sm:text-sm"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export CSV
          </MotionButton>
        </div>
      </div>

      <section className="overflow-hidden rounded-2xl bg-[#eaf1ff] sm:rounded-3xl">
        <div className="md:hidden">
          {pagedRows.length > 0 ? (
            <div className="space-y-3 p-3 sm:p-4">
              {pagedRows.map((row, index) => (
                <motion.article
                  key={row.id}
                  className="rounded-xl bg-white/75 p-4"
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: shouldReduceMotion ? MOTION_DURATION.fast : MOTION_DURATION.base,
                    ease: MOTION_EASE.standard,
                    delay: shouldReduceMotion ? 0 : index * 0.04,
                  }}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="text-sm font-black text-[#b60055]">{row.id}</p>
                    {row.error ? (
                      <div className="flex w-fit items-center gap-1.5 rounded-md bg-[#fb5151]/10 px-2.5 py-1 text-[#b31b25]">
                        <span className="material-symbols-outlined text-sm">error</span>
                        <span className="text-[10px] font-bold uppercase tracking-[0.1em]">{row.status}</span>
                      </div>
                    ) : (
                      <div className="flex w-fit items-center gap-1.5 rounded-md bg-green-50 px-2.5 py-1 text-green-700">
                        <span className="material-symbols-outlined text-sm">check_circle</span>
                        <span className="text-[10px] font-bold uppercase tracking-[0.1em]">{row.status}</span>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="mb-1 font-semibold uppercase tracking-[0.08em] text-[#68788f]">Input A</p>
                      <p className="text-sm font-medium text-[#203044]">{row.inputA}</p>
                    </div>
                    <div>
                      <p className="mb-1 font-semibold uppercase tracking-[0.08em] text-[#68788f]">Input B</p>
                      <p className="text-sm font-medium text-[#203044]">{row.inputB}</p>
                    </div>
                    <div>
                      <p className="mb-1 font-semibold uppercase tracking-[0.08em] text-[#68788f]">Operation</p>
                      <span className="inline-flex rounded-full bg-[#c9deff] px-2.5 py-1 text-[10px] font-bold text-[#3c4c61]">{row.operation}</span>
                    </div>
                    <div>
                      <p className="mb-1 font-semibold uppercase tracking-[0.08em] text-[#68788f]">Result</p>
                      <p className={`text-sm font-black ${row.error ? "italic text-[#b31b25]" : "text-[#203044]"}`}>{row.result}</p>
                    </div>
                  </div>

                  <p className="mt-3 text-[11px] text-[#68788f]">{row.timestamp}</p>
                </motion.article>
              ))}
            </div>
          ) : (
            <p className="p-4 text-sm text-[#4d5d73]">No transactions available for this filter.</p>
          )}
        </div>

        <div className="hidden md:block">
          <div className="maas-scrollbar overflow-x-auto">
            <table className="min-w-full text-left">
              <thead className="bg-[#dce9ff] text-[#4d5d73]">
                <tr>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Transaction ID</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Input A</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Operation</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Input B</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Result</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Timestamp</th>
                  <th className="px-4 py-4 text-[10px] font-black uppercase tracking-[0.15em] lg:px-6">Status</th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.length > 0 ? (
                  pagedRows.map((row, index) => (
                    <motion.tr
                      key={row.id}
                      className={index % 2 === 1 ? "bg-white/40" : undefined}
                      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: shouldReduceMotion ? MOTION_DURATION.fast : MOTION_DURATION.base,
                        ease: MOTION_EASE.standard,
                        delay: shouldReduceMotion ? 0 : index * 0.04,
                      }}
                    >
                      <td className="px-4 py-4 text-sm font-bold text-[#b60055] lg:px-6">{row.id}</td>
                      <td className="px-4 py-4 text-sm font-medium lg:px-6">{row.inputA}</td>
                      <td className="px-4 py-4 lg:px-6">
                        <span className="rounded-full bg-[#c9deff] px-3 py-1 text-[10px] font-bold text-[#3c4c61]">{row.operation}</span>
                      </td>
                      <td className="px-4 py-4 text-sm font-medium lg:px-6">{row.inputB}</td>
                      <td className={`px-4 py-4 text-sm font-black lg:px-6 ${row.error ? "italic text-[#b31b25]" : "text-[#203044]"}`}>{row.result}</td>
                      <td className="px-4 py-4 text-xs text-[#68788f] lg:px-6">{row.timestamp}</td>
                      <td className="px-4 py-4 lg:px-6">
                        {row.error ? (
                          <div className="flex w-fit items-center gap-2 rounded-md bg-[#fb5151]/10 px-3 py-1.5 text-[#b31b25]">
                            <span className="material-symbols-outlined text-sm">error</span>
                            <span className="text-[10px] font-bold uppercase tracking-[0.1em]">{row.status}</span>
                          </div>
                        ) : (
                          <div className="flex w-fit items-center gap-2 rounded-md bg-green-50 px-3 py-1.5 text-green-700">
                            <span className="material-symbols-outlined text-sm">check_circle</span>
                            <span className="text-[10px] font-bold uppercase tracking-[0.1em]">{row.status}</span>
                          </div>
                        )}
                      </td>
                    </motion.tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-4 py-8 text-sm text-[#4d5d73] lg:px-6" colSpan={7}>
                      No transactions available for this filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#dce9ff] px-4 py-4 lg:px-6">
          <p className="text-xs text-[#4d5d73]">
            Showing <span className="font-bold">{pagedRows.length}</span> of {filteredRows.length} transactions
          </p>
          <div className="flex items-center gap-2">
            <MotionButton
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1}
              className="maas-touch-target flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[#4d5d73] disabled:opacity-40"
              ariaLabel="Previous page"
            >
              <span className="material-symbols-outlined">chevron_left</span>
            </MotionButton>
            <span className="flex h-11 min-w-11 items-center justify-center rounded-lg bg-[#b60055] px-3 text-xs font-bold text-white">{page}</span>
            <MotionButton
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages}
              className="maas-touch-target flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[#4d5d73] disabled:opacity-40"
              ariaLabel="Next page"
            >
              <span className="material-symbols-outlined">chevron_right</span>
            </MotionButton>
          </div>
        </div>
      </section>

      <section className="mt-10 grid grid-cols-1 gap-6 lg:mt-12 lg:grid-cols-12 lg:gap-8">
        <MotionCard className="lg:col-span-7">
          <article className="flex flex-col items-start gap-6 rounded-3xl bg-[#c9deff] p-5 sm:p-6 md:flex-row md:items-center md:p-8">
            <div className="flex-1">
              <h3 className="text-lg font-extrabold sm:text-xl">Computational Load</h3>
              <p className="mb-5 mt-2 text-sm text-[#4d5d73] sm:mb-6">
                Your current history represents 4.2% of your available enterprise storage capacity.
              </p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-[#eaf1ff]">
                <div className="maas-enterprise-gradient h-full w-[4.2%]" />
              </div>
            </div>
            <div className="maas-enterprise-gradient flex h-20 w-20 shrink-0 rotate-3 items-center justify-center rounded-2xl text-white shadow-lg sm:h-24 sm:w-24">
              <span className="material-symbols-outlined text-3xl sm:text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                analytics
              </span>
            </div>
          </article>
        </MotionCard>

        <MotionCard className="lg:col-span-5">
          <article className="rounded-3xl border border-[#9eaec7]/15 bg-[#eaf1ff] p-5 sm:p-6 md:p-8">
            <h3 className="mb-5 text-xs font-black uppercase tracking-[0.15em] text-[#4d5d73] sm:mb-6 sm:text-sm">Quick Analysis</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm">Uptime Success</span>
                <span className="text-sm font-black text-green-700">99.98%</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm">Avg Latency</span>
                <span className="text-sm font-black text-[#b60055]">12ms</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm">Error Rate</span>
                <span className="text-sm font-black text-[#b31b25]">0.02%</span>
              </div>
            </div>
          </article>
        </MotionCard>
      </section>
    </>
  );
}
