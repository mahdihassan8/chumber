import { resolveAssetUrl } from "@/utils/assets";

export function ProductImage({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  const resolved = resolveAssetUrl(src);
  if (resolved) {
    // object-contain on mobile so the image is never cropped to fill its
    // box; object-cover from sm: up keeps the existing desktop look, where
    // the fixed-size boxes were already tuned for it.
    return <img src={resolved} alt={alt} className={`object-contain object-center sm:object-cover ${className}`} loading="lazy" />;
  }
  return (
    <div className={`flex items-center justify-center bg-gradient-to-br from-brand-50 to-zinc-100 ${className}`}>
      <svg className="h-10 w-10 text-brand-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
        />
      </svg>
    </div>
  );
}
