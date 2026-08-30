import { useToast } from "@/context/ToastContext";
import type { ToastVariant } from "@/context/ToastContext";

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "bg-zinc-900 text-white",
  error: "bg-red-600 text-white",
  info: "bg-zinc-900 text-white",
};

const VARIANT_ICON: Record<ToastVariant, string> = {
  success: "M4.5 12.75l6 6 9-13.5",
  error: "M12 9v3.75m0 3.75h.008M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  info: "M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z",
};

export function ToastContainer() {
  const { toasts, dismissToast } = useToast();

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4 sm:items-end sm:right-4 sm:left-auto">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto flex w-full max-w-sm animate-slide-in-right items-start gap-2.5 rounded-lg px-4 py-3 shadow-lg ${VARIANT_STYLES[toast.variant]}`}
          role="status"
        >
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d={VARIANT_ICON[toast.variant]} />
          </svg>
          <p className="flex-1 text-sm font-medium">{toast.message}</p>
          <button onClick={() => dismissToast(toast.id)} className="shrink-0 text-white/70 hover:text-white" aria-label="Dismiss">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
