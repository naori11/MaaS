"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { MotionButton, MotionCard } from "../_components/motion/motion-primitives";
import { MOTION_DURATION, MOTION_EASE } from "../_lib/motion/tokens";
import { getSeedHistoryRows, loadHistoryRows, toHistoryCsv, type HistoryRow } from "../_lib/mock-history";

type FilterMode = "all" | "success" | "errors";

const PAGE_SIZE = 6;

export default function HistoryPage() {
  const shouldReduceMotion = useReducedMotion();
  const [rows, setRows] = useState<HistoryRow[]>(getSeedHistoryRows());
  const [filter, setFilter] = useState<FilterMode>("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setRows(loadHistoryRows());
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
      <div className="flex flex-wrap justify-between gap-4 pb-10">
        <div className="max-w-2xl">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.1em] text-[#b60055]">Enterprise Logs</p>
        </div>
        <div className="flex gap-4">
          <MotionButton
            type="button"
            onClick={handleFilterCycle}
            className="flex items-center gap-2 rounded-lg bg-[#dce9ff] px-6 py-2.5 text-sm font-semibold"
          >
            <span className="material-symbols-outlined text-sm">filter_list</span>
            {filterLabel}
          </MotionButton>
          <MotionButton
            type="button"
            onClick={exportCsv}
            className="maas-enterprise-gradient flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#b60055]/20"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export CSV
          </MotionButton>
        </div>
      </div>

      <section className="overflow-hidden rounded-3xl bg-[#eaf1ff]">
        <div className="maas-scrollbar overflow-x-auto">
          <table className="min-w-full text-left">
            <thead className="bg-[#dce9ff] text-[#4d5d73]">
              <tr>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Transaction ID</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Input A</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Operation</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Input B</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Result</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Timestamp</th>
                <th className="px-8 py-5 text-[10px] font-black uppercase tracking-[0.15em]">Status</th>
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
                    <td className="px-8 py-6 text-sm font-bold text-[#b60055]">{row.id}</td>
                    <td className="px-8 py-6 text-sm font-medium">{row.inputA}</td>
                    <td className="px-8 py-6">
                      <span className="rounded-full bg-[#c9deff] px-3 py-1 text-[10px] font-bold text-[#3c4c61]">{row.operation}</span>
                    </td>
                    <td className="px-8 py-6 text-sm font-medium">{row.inputB}</td>
                    <td className={`px-8 py-6 text-sm font-black ${row.error ? "italic text-[#b31b25]" : "text-[#203044]"}`}>{row.result}</td>
                    <td className="px-8 py-6 text-xs text-[#68788f]">{row.timestamp}</td>
                    <td className="px-8 py-6">
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
                  <td className="px-8 py-8 text-sm text-[#4d5d73]" colSpan={7}>
                    No transactions available for this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between bg-[#dce9ff] px-8 py-5">
          <p className="text-xs text-[#4d5d73]">
            Showing <span className="font-bold">{pagedRows.length}</span> of {filteredRows.length} transactions
          </p>
          <div className="flex gap-2">
            <MotionButton
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1}
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-[#4d5d73] disabled:opacity-40"
              ariaLabel="Previous page"
            >
              <span className="material-symbols-outlined">chevron_left</span>
            </MotionButton>
            <span className="flex h-10 min-w-10 items-center justify-center rounded-lg bg-[#b60055] px-3 text-xs font-bold text-white">{page}</span>
            <MotionButton
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages}
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-[#4d5d73] disabled:opacity-40"
              ariaLabel="Next page"
            >
              <span className="material-symbols-outlined">chevron_right</span>
            </MotionButton>
          </div>
        </div>
      </section>

      <section className="mt-12 grid grid-cols-12 gap-8">
        <MotionCard className="col-span-12 lg:col-span-7">
          <article className="flex items-center gap-8 rounded-3xl bg-[#c9deff] p-8">
            <div className="flex-1">
              <h3 className="text-xl font-extrabold">Computational Load</h3>
              <p className="mb-6 mt-2 text-sm text-[#4d5d73]">Your current history represents 4.2% of your available enterprise storage capacity.</p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-[#eaf1ff]">
                <div className="maas-enterprise-gradient h-full w-[4.2%]" />
              </div>
            </div>
            <div className="maas-enterprise-gradient flex h-24 w-24 rotate-3 items-center justify-center rounded-2xl text-white shadow-lg">
              <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                analytics
              </span>
            </div>
          </article>
        </MotionCard>

        <MotionCard className="col-span-12 lg:col-span-5">
          <article className="rounded-3xl border border-[#9eaec7]/15 bg-[#eaf1ff] p-8">
            <h3 className="mb-6 text-sm font-black uppercase tracking-[0.15em] text-[#4d5d73]">Quick Analysis</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Uptime Success</span>
                <span className="text-sm font-black text-green-700">99.98%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Avg Latency</span>
                <span className="text-sm font-black text-[#b60055]">12ms</span>
              </div>
              <div className="flex items-center justify-between">
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
