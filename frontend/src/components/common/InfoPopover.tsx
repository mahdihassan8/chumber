import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

interface InfoPopoverProps {
  label: string;
  title: string;
  children: ReactNode;
}

const POPOVER_WIDTH = 256; // px, matches w-64
const VIEWPORT_MARGIN = 16; // px of breathing room from the screen edge

export function InfoPopover({ label, title, children }: InfoPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [offsetX, setOffsetX] = useState(0);
  const anchorRef = useRef<HTMLDivElement>(null);

  // The icon can sit anywhere in the header, so the popover's horizontal
  // offset is computed relative to it and clamped to the viewport — a static
  // centered class would overflow off-screen on narrow phones.
  useLayoutEffect(() => {
    if (!isOpen || !anchorRef.current) return;

    const reposition = () => {
      const rect = anchorRef.current!.getBoundingClientRect();
      const idealLeft = rect.left + rect.width / 2 - POPOVER_WIDTH / 2;
      const maxLeft = window.innerWidth - POPOVER_WIDTH - VIEWPORT_MARGIN;
      const clampedLeft = Math.min(Math.max(idealLeft, VIEWPORT_MARGIN), maxLeft);
      setOffsetX(clampedLeft - rect.left);
    };

    reposition();
    window.addEventListener("resize", reposition);
    return () => window.removeEventListener("resize", reposition);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen]);

  return (
    <div className="relative inline-block" ref={anchorRef}>
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-label={label}
        aria-expanded={isOpen}
        className="flex h-5 w-5 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="8" x2="12" y2="13" strokeLinecap="round" />
          <circle cx="12" cy="16.5" r="0.75" fill="currentColor" stroke="none" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div
            role="dialog"
            aria-label={title}
            style={{ left: offsetX, width: POPOVER_WIDTH }}
            className="absolute top-full z-20 mt-2 animate-fade-in rounded-xl border border-zinc-200 bg-white p-4 shadow-lg"
          >
            <p className="text-sm font-semibold text-zinc-900">{title}</p>
            <div className="mt-2 space-y-1.5">{children}</div>
          </div>
        </>
      )}
    </div>
  );
}
