import { formatBeans } from "@/utils/assets";

/** Renders a Beans amount with the currency icon beside it (e.g. "1 [icon]").
 * Font size/weight/color are inherited from the surrounding element, so drop
 * this in wherever `{formatBeans(x)}` used to sit and it picks up the same
 * styling. Icon size tracks the surrounding text size (em-based) so it stays
 * proportional at every call site and on mobile. */
export function BeansAmount({ amount }: { amount: number }) {
  return (
    <span className="inline-flex items-center gap-1">
      {formatBeans(amount)}
      <img src="/bean-icon.png" alt="" className="h-[0.9em] w-[0.9em] shrink-0 object-contain" />
    </span>
  );
}
