import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  tone?: "default" | "warning";
  /** Extra classes for the value text itself -- e.g. to color a signed
   * figure like Balance Difference green/red. Additive to (not a
   * replacement for) the base text styling, and independent of `tone`
   * (which only affects the icon badge). */
  valueClassName?: string;
}

export function StatCard({ label, value, icon, tone = "default", valueClassName = "" }: StatCardProps) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${tone === "warning" ? "bg-amber-100 text-amber-700" : "bg-brand-100 text-brand-700"}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm text-zinc-500">{label}</p>
        <p className={`text-xl font-bold ${valueClassName || "text-zinc-900"}`}>{value}</p>
      </div>
    </div>
  );
}
