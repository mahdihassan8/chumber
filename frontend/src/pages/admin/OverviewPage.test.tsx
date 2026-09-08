import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { OverviewPage } from "@/pages/admin/OverviewPage";
import { getOverview } from "@/api/admin";
import type { OverviewStats } from "@/types";

vi.mock("@/api/admin", () => ({
  getOverview: vi.fn(),
}));

// ChumberRequiredCard fetches its own data on mount -- irrelevant to what
// this page's own stats/formatting look like, so it's stubbed out.
vi.mock("@/components/admin/ChumberRequiredCard", () => ({
  ChumberRequiredCard: () => <div>Chumber Required stub</div>,
}));

function makeStats(balance_difference: number): OverviewStats {
  return {
    total_users: 10,
    total_customers: 8,
    total_admins: 2,
    total_products: 5,
    available_products: 4,
    out_of_stock_products: 1,
    total_orders: 3,
    total_balance_distributed: 100_000,
    total_user_balance: 600_000,
    total_inventory_value: 1_000_000,
    balance_difference,
    recent_orders: [],
    recent_transactions: [],
  };
}

function renderOverview(balance_difference: number) {
  vi.mocked(getOverview).mockResolvedValue(makeStats(balance_difference));
  return render(
    <MemoryRouter>
      <OverviewPage />
    </MemoryRouter>
  );
}

describe("OverviewPage - Balance Difference", () => {
  it("shows a positive difference with a + sign, in green", async () => {
    renderOverview(300_000);

    const value = await screen.findByText("+300,000 IQD");
    expect(value).toHaveClass("text-green-600");
  });

  it("shows a negative difference with a - sign, in red", async () => {
    renderOverview(-300_000);

    const value = await screen.findByText("-300,000 IQD");
    expect(value).toHaveClass("text-red-600");
  });

  it("shows exactly zero with no sign, in the dashboard's neutral styling", async () => {
    renderOverview(0);

    const value = await screen.findByText("0 IQD");
    expect(value).not.toHaveClass("text-green-600");
    expect(value).not.toHaveClass("text-red-600");
    expect(value).toHaveClass("text-zinc-900");
  });
});

describe("OverviewPage - Total Debts removal", () => {
  it("no longer renders a Total Debts section or stat anywhere on the page", async () => {
    renderOverview(300_000);

    await waitFor(() => expect(screen.getByText("+300,000 IQD")).toBeInTheDocument());
    expect(screen.queryByText(/Total Debts/i)).not.toBeInTheDocument();
  });
});
