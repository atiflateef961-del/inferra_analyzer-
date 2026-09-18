"use client";

import { useState } from "react";
import { Brain, CircleAlert, CloudSun, Gauge, Smile } from "lucide-react";

const moods = [
  {
    label: "Clear",
    detail: "Momentum is strong",
    icon: Smile,
    tone: "emerald",
    readout: "Keep the team moving on high-confidence decisions today.",
  },
  {
    label: "Focused",
    detail: "A few priorities need attention",
    icon: Gauge,
    tone: "sky",
    readout: "Protect the afternoon for the invoice and inventory queues.",
  },
  {
    label: "Watchful",
    detail: "Signals are mixed",
    icon: CircleAlert,
    tone: "amber",
    readout: "Review the cost movement before approving new supplier orders.",
  },
] as const;

const toneClasses = {
  emerald: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  sky: "border-sky-400/30 bg-sky-500/10 text-sky-200",
  amber: "border-amber-400/30 bg-amber-500/10 text-amber-200",
};

export function DayMood() {
  const [selectedMood, setSelectedMood] = useState(1);
  const activeMood = moods[selectedMood];
  const ActiveIcon = activeMood.icon;

  return (
    <section className="glass-card mb-6 rounded-[28px] p-5 sm:p-6" aria-labelledby="day-mood-title">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-200 ring-1 ring-violet-400/20">
            <CloudSun className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm text-slate-300">Today&apos;s operating read</p>
            <h3 id="day-mood-title" className="mt-1 text-xl font-semibold text-white">Day mood</h3>
            <p className="mt-1 flex items-center gap-2 text-sm text-slate-400">
              <Brain className="h-3.5 w-3.5 text-violet-300" />
              {activeMood.readout}
            </p>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-3 lg:min-w-[460px]">
          {moods.map(({ label, detail, icon: Icon, tone }, index) => {
            const isSelected = selectedMood === index;

            return (
              <button
                key={label}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setSelectedMood(index)}
                className={`rounded-2xl border px-3 py-3 text-left transition ${
                  isSelected ? toneClasses[tone] : "border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.07]"
                }`}
              >
                <span className="flex items-center gap-2 text-sm font-medium">
                  <Icon className="h-4 w-4" />
                  {label}
                </span>
                <span className="mt-1 block text-xs text-slate-400">{detail}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-5 flex items-center gap-2 border-t border-white/10 pt-4 text-xs text-slate-400">
        <ActiveIcon className="h-3.5 w-3.5 text-slate-300" />
        Mood is a lightweight team check-in and can be updated as priorities shift.
      </div>
    </section>
  );
}
