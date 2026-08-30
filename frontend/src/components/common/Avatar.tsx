import { resolveAssetUrl, initials } from "@/utils/assets";

interface AvatarProps {
  src?: string | null;
  name: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const SIZE_CLASS = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-14 w-14 text-lg",
  xl: "h-24 w-24 text-2xl",
};

export function Avatar({ src, name, size = "md" }: AvatarProps) {
  const resolved = resolveAssetUrl(src);
  return (
    <div className={`flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-100 font-semibold text-brand-700 ${SIZE_CLASS[size]}`}>
      {resolved ? <img src={resolved} alt={name} className="h-full w-full object-cover object-center" /> : <span>{initials(name)}</span>}
    </div>
  );
}
