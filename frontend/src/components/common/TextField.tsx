import { forwardRef, type InputHTMLAttributes } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(({ label, error, hint, id, className = "", ...props }, ref) => {
  const fieldId = id ?? props.name;
  return (
    <div>
      {label && (
        <label htmlFor={fieldId} className="label">
          {label}
        </label>
      )}
      <input ref={ref} id={fieldId} className={`input ${error ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : ""} ${className}`} {...props} />
      {hint && !error && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
      {error && <p className="mt-1 text-xs font-medium text-red-600">{error}</p>}
    </div>
  );
});
TextField.displayName = "TextField";
