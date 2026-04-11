"use client";

import { MotionButton, MotionSection } from "../../_components/motion/motion-primitives";

const rows = [
  ["AC", "+/-", "%", "÷"],
  ["7", "8", "9", "×"],
  ["4", "5", "6", "−"],
  ["1", "2", "3", "+"],
  ["0", ".", "="],
];

const isAction = (value: string) => ["÷", "×", "−", "+", "="].includes(value);

export default function CalculatorFocusedPage() {
  return (
    <>
      <MotionSection className="relative mx-auto w-full max-w-lg">
        <div className="maas-enterprise-gradient absolute -inset-4 rounded-full opacity-10 blur-3xl" />

        <article className="maas-glass-panel relative overflow-hidden rounded-[2.5rem] border border-white/40 p-8 shadow-2xl">
          <div className="group relative mb-8 flex min-h-[140px] flex-col items-end justify-end overflow-hidden rounded-2xl bg-[#000f21] p-8">
            <div
              className="pointer-events-none absolute inset-0 opacity-10"
              style={{
                backgroundImage: "radial-gradient(#4d5d73 1px, transparent 0)",
                backgroundSize: "8px 8px",
              }}
            />
            <div className="mb-1 text-sm font-medium uppercase tracking-[0.15em] text-[#edf3ff]/40">Current Expression</div>
            <div className="mb-2 max-w-full truncate text-right text-xs uppercase tracking-[0.1em] text-[#edf3ff]/40">0</div>
            <output className="text-5xl font-bold tracking-tight text-white md:text-6xl" aria-live="polite" aria-label="Calculator result">
              0
            </output>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {rows.flatMap((row, rowIndex) =>
              row.map((item, colIndex) => {
                const wide = item === "0" && rowIndex === 4;
                const action = isAction(item);
                const utility = ["AC", "+/-", "%"].includes(item);

                return (
                  <MotionButton
                    key={`${rowIndex}-${item}`}
                    type="button"
                    className={`h-16 rounded-2xl font-bold transition active:scale-95 ${wide ? "col-span-2 px-8 text-left" : ""} ${
                      action
                        ? "maas-enterprise-gradient text-2xl text-white shadow-lg shadow-[#b60055]/20"
                        : utility
                          ? "bg-[#c9deff] text-lg text-[#203044]"
                          : "bg-white text-xl text-[#203044]"
                    }`}
                  >
                    <span style={wide && colIndex === 0 ? { textAlign: "left", display: "inline-block", width: "100%" } : undefined}>{item}</span>
                  </MotionButton>
                );
              }),
            )}
          </div>

          <div className="mt-8 flex justify-center opacity-30">
            <p className="text-[10px] font-bold uppercase tracking-[0.4em]">Proprietary Math Engine</p>
          </div>
        </article>
      </MotionSection>

      <div className="pointer-events-none fixed bottom-0 right-0 hidden select-none p-12 opacity-5 xl:block">
        <span className="text-[20rem] font-black leading-none tracking-tight">Σ</span>
      </div>
    </>
  );
}
