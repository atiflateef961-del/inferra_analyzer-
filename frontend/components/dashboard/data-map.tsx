"use client";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";
import { formatMoney } from "@/lib/api";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import worldMap from "world-atlas/countries-110m.json";

const locationCoordinates: Record<string, [number, number]> = {
  "united states": [-100, 38], usa: [-100, 38], canada: [-106, 57], mexico: [-102, 23],
  brazil: [-52, -10], argentina: [-64, -34], chile: [-71, -33], colombia: [-74, 4],
  "united kingdom": [-3, 55], uk: [-3, 55], germany: [10, 51], france: [2, 46],
  spain: [-4, 40], italy: [12, 42], netherlands: [5, 52], switzerland: [8, 47],
  india: [79, 22], china: [104, 35], japan: [138, 36], singapore: [104, 1],
  australia: [134, -25], "south africa": [24, -30], nigeria: [8, 9], egypt: [30, 27],
  "new york": [-74, 41], london: [0, 51], berlin: [13, 52], paris: [2, 49], tokyo: [139, 36],
};

function coordinatesFor(location: { name: string; latitude?: number; longitude?: number }): [number, number] | null {
  if (typeof location.latitude === "number" && typeof location.longitude === "number") {
    return [location.longitude, location.latitude];
  }
  return locationCoordinates[location.name.trim().toLowerCase()] ?? null;
}

export function DataMap() {
  const { analytics } = useDashboardData();
  const periods = analytics?.series ?? [];
  const categories = analytics?.categories ?? [];
  const locations = analytics?.locations ?? [];
  const maxValue = Math.max(1, ...periods.flatMap((item) => [item.revenue, item.expense, Math.abs(item.profit)]));

  return (
    <section className="glass-card mt-6 rounded-[28px] p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-slate-300">Imported data map</p>
          <h3 className="text-xl font-semibold text-white">Revenue, loss, profit, and categories</h3>
        </div>
        <p className="text-xs text-slate-400">Every bar comes from the uploaded files</p>
      </div>

      {periods.length === 0 && categories.length === 0 && locations.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-white/10 p-6 text-sm text-slate-400">Import a file with readable rows or financial values to populate the map.</div>
      ) : (
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
          <div className="space-y-4">
            {periods.map((item) => (
              <div key={item.month} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-3 flex items-center justify-between gap-3"><span className="text-sm font-medium text-white">{item.month}</span><span className="text-xs text-slate-400">Profit {formatMoney(item.profit)}</span></div>
                {[["Revenue", item.revenue, "bg-emerald-400"], ["Expense", item.expense, "bg-amber-400"], ["Profit", Math.abs(item.profit), "bg-violet-400"]].map(([label, value, color]) => (
                  <div key={String(label)} className="mb-2 last:mb-0"><div className="mb-1 flex justify-between text-[11px] text-slate-400"><span>{label}</span><span>{formatMoney(Number(value))}</span></div><div className="h-2 rounded-full bg-white/10"><div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(100, (Number(value) / maxValue) * 100)}%` }} /></div></div>
                ))}
              </div>
            ))}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-sm font-medium text-white">Category map</p>
            <div className="mt-4 space-y-3">{categories.length ? categories.map((item) => <div key={item.category} className="flex items-center justify-between gap-3 text-sm"><span className="truncate text-slate-300">{item.category}</span><span className="font-medium text-emerald-300">{formatMoney(item.sales)}</span></div>) : <p className="text-sm text-slate-400">No category column was detected.</p>}</div>
          </div>
        </div>
      )}

      {locations.length ? (
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/45">
            <ComposableMap projectionConfig={{ scale: 145 }} width={800} height={380} style={{ width: "100%", height: "auto" }}>
              <Geographies geography={worldMap as unknown as string}>
                {({ geographies }) => geographies.map((geography) => <Geography key={geography.rsmKey} geography={geography} fill="#1e293b" stroke="#475569" strokeWidth={0.45} />)}
              </Geographies>
              {locations.map((location) => {
                const coordinates = coordinatesFor(location);
                if (!coordinates) return null;
                const intensity = Math.min(18, Math.max(7, Math.abs(location.profit) / Math.max(1, Math.abs(locations[0]?.profit ?? 1)) * 18));
                return <Marker key={location.name} coordinates={coordinates}><circle r={intensity} fill={location.profit >= 0 ? "#34d399" : "#fb7185"} fillOpacity={0.25} stroke={location.profit >= 0 ? "#6ee7b7" : "#fda4af"} strokeWidth={1.5} /><circle r={3} fill={location.profit >= 0 ? "#a7f3d0" : "#fecdd3"} /><title>{`${location.name}: ${formatMoney(location.profit)} profit`}</title></Marker>;
              })}
            </ComposableMap>
            <div className="flex gap-4 border-t border-white/10 px-4 py-3 text-[11px] text-slate-400"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-300" />Profit</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-rose-300" />Loss</span><span>Markers use recognized country/city names</span></div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-sm font-medium text-white">Geographic results</p>
            <div className="mt-4 space-y-3">{locations.map((location) => <div key={location.name} className="flex items-center justify-between gap-3 border-b border-white/5 pb-3 last:border-0"><div className="min-w-0"><p className="truncate text-sm text-slate-200">{location.name}</p><p className="text-xs text-slate-500">Revenue {formatMoney(location.revenue)} · Expense {formatMoney(location.expense)}</p></div><span className={location.profit >= 0 ? "text-sm font-medium text-emerald-300" : "text-sm font-medium text-rose-300"}>{formatMoney(location.profit)}</span></div>)}</div>
          </div>
        </div>
      ) : null}
    </section>
  );
}