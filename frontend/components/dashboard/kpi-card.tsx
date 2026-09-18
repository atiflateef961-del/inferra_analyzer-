import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

export type KpiCardProps = {
  label: string;
  value: string;
  delta: string;
  trend: "up" | "down";
  icon: LucideIcon;
};

export function KpiCard({ label, value, delta, trend, icon: Icon }: KpiCardProps) {
  const isPositive = trend === "up";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="glass-card h-full p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-300 ring-1 ring-white/10">
          <Icon className="h-5 w-5" />
        </div>
        <div
          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${
            isPositive
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
              : "border-rose-400/30 bg-rose-400/10 text-rose-200"
          }`}
        >
          {isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
          {delta}
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-sm text-slate-300">{label}</p>
        <h3 className="text-2xl font-semibold tracking-tight text-white">{value}</h3>
      </div>
    </motion.div>
  );
}
