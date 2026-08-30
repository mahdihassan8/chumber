import { Badge } from "@/components/common/Badge";

export function StockBadge({ stock, isAvailable }: { stock: number; isAvailable: boolean }) {
  if (!isAvailable || stock === 0) return <Badge color="red">Out of stock</Badge>;
  if (stock <= 5) return <Badge color="amber">Only {stock} left</Badge>;
  return <Badge color="green">In stock</Badge>;
}
