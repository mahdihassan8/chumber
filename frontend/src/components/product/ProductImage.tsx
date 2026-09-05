import { resolveAssetUrl } from "@/utils/assets";

/** Renders a product image inside the fixed-size box the caller supplies.
 *
 * object-contain at every breakpoint: uploaded images come in whatever aspect
 * ratio the admin had (the current ones are wide 1408x768 canvases with the
 * product in the middle), so cropping to fill would cut the product's sides
 * off and, in the larger boxes, scale it past its native size until it looked
 * soft. Contain keeps the whole product visible, never stretches it, and means
 * the image is only ever scaled down. The neutral plate fills whatever
 * letterbox space is left over when the ratios don't match. */
export function ProductImage({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  const resolved = resolveAssetUrl(src);
  if (resolved) {
    return <img src={resolved} alt={alt} className={`bg-zinc-50 object-contain object-center p-1 ${className}`} loading="lazy" />;
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
