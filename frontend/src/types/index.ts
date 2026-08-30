export type UserRole = "customer" | "admin";
export type Currency = "USD" | "IQD";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  balance: number;
  /** The currency this account's balance is denominated in — admin-selectable,
   * never converted. Drives formatting everywhere the balance is shown. */
  currency: Currency;
  avatar_url: string | null;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  image_url: string | null;
  is_active: boolean;
  is_available: boolean;
  created_at: string;
}

export interface CartItem {
  id: string;
  product: Product;
  quantity: number;
  subtotal: number;
}

export interface Cart {
  items: CartItem[];
  total: number;
  balance: number;
}

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
}

export type OrderStatus = "completed" | "cancelled";

export interface Order {
  id: string;
  user_id: string;
  user_username: string;
  user_full_name: string;
  total_amount: number;
  status: OrderStatus;
  created_at: string;
  items: OrderItem[];
}

export interface CheckoutResponse {
  order: Order;
  new_balance: number;
}

export type TransactionType = "admin_recharge" | "purchase" | "refund" | "adjustment";

export interface BalanceTransaction {
  id: string;
  user_id: string;
  amount: number;
  /** Derived server-side from the owning account's *current* User.currency
   * — not admin-selectable per transaction. Lets a transaction list spanning
   * multiple accounts (admin overview's recent-activity feed) render each
   * row in its own account's currency. */
  currency: Currency;
  transaction_type: TransactionType;
  related_order_id: string | null;
  created_by_id: string | null;
  created_by_username: string | null;
  description: string | null;
  created_at: string;
}

export interface Balance {
  balance: number;
  /** The account's currency — see User.currency. Every transaction below
   * carries this same value, since a balance's ledger can never mix
   * currencies. */
  currency: Currency;
  total_received: number;
  total_spent: number;
  transactions: BalanceTransaction[];
}

export type AIInputType = "text" | "voice";
export type AIRequestStatus = "pending" | "confirmed" | "rejected" | "failed";

export interface AIRestockRequest {
  id: string;
  raw_input: string;
  input_type: AIInputType;
  parsed_action: string | null;
  parsed_product_name: string | null;
  parsed_quantity: number | null;
  resolved_product_id: string | null;
  resolved_product_name: string | null;
  current_stock: number | null;
  status: AIRequestStatus;
  error_message: string | null;
  created_at: string;
}

export interface OverviewStats {
  total_users: number;
  total_customers: number;
  total_admins: number;
  total_products: number;
  available_products: number;
  out_of_stock_products: number;
  total_orders: number;
  total_balance_distributed: number;
  recent_orders: Order[];
  recent_transactions: BalanceTransaction[];
}

export interface GiveawayWinner {
  id: string;
  username: string;
  full_name: string;
}

export interface GiveawayResult {
  /** False when nothing has ever been revealed yet — every field below is
   * meaningless in that case. */
  available: boolean;
  scheduled_date: string | null;
  product_name: string | null;
  product_image_url: string | null;
  winners: GiveawayWinner[];
  /** Computed entirely server-side from the caller's authenticated
   * identity — this is never something the frontend calculates. */
  is_winner: boolean;
}

export interface ApiError {
  detail: string | { msg: string; loc: (string | number)[] }[];
}
