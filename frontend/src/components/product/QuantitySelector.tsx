interface QuantitySelectorProps {
  quantity: number;
  max: number;
  min?: number;
  onChange: (quantity: number) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function QuantitySelector({ quantity, max, min = 1, onChange, disabled = false, size = "md" }: QuantitySelectorProps) {
  const dec = () => onChange(Math.max(min, quantity - 1));
  const inc = () => onChange(Math.min(max, quantity + 1));

  const btnSize = size === "sm" ? "h-7 w-7 text-sm" : "h-9 w-9";
  const boxWidth = size === "sm" ? "w-8 text-sm" : "w-10";

  return (
    <div className="inline-flex items-center rounded-lg border border-zinc-200 bg-white">
      <button
        type="button"
        onClick={dec}
        disabled={disabled || quantity <= min}
        aria-label="Decrease quantity"
        className={`flex ${btnSize} items-center justify-center rounded-l-lg text-zinc-600 transition-colors hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent`}
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
        </svg>
      </button>
      <span className={`flex ${boxWidth} items-center justify-center font-semibold text-zinc-900 tabular-nums`}>{quantity}</span>
      <button
        type="button"
        onClick={inc}
        disabled={disabled || quantity >= max}
        aria-label="Increase quantity"
        className={`flex ${btnSize} items-center justify-center rounded-r-lg text-zinc-600 transition-colors hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent`}
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>
    </div>
  );
}
