import type { ReactNode } from "react";

type BadgeColor = "green" | "red" | "amber" | "zinc" | "blue";

const COLOR_CLASS: Record<BadgeColor, string> = {
  green: "bg-green-50 text-green-700 ring-green-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  zinc: "bg-zinc-100 text-zinc-700 ring-zinc-500/20",
  blue: "bg-brand-50 text-brand-700 ring-brand-600/20",
};

export function Badge({ children, color = "zinc" }: { children: ReactNode; color?: BadgeColor }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${COLOR_CLASS[color]}`}>
      {children}
    </span>
  );
}
