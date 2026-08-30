import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Spinner } from "@/components/common/Spinner";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  isLoading?: boolean;
  fullWidth?: boolean;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  danger: "btn-danger",
  ghost: "btn-ghost",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", isLoading = false, fullWidth = false, disabled, className = "", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${VARIANT_CLASS[variant]} px-4 py-2.5 text-sm ${fullWidth ? "w-full" : ""} ${className}`}
        {...props}
      >
        {isLoading && <Spinner size="sm" className={variant === "primary" || variant === "danger" ? "text-white" : ""} />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
