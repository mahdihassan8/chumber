import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BalanceProvider, useBalance } from "@/context/BalanceContext";
import { getMyBalance } from "@/api/balance";

// A stable object reference, matching how the real AuthContext's useState
// value stays referentially stable across re-renders that don't change it --
// a fresh literal here would destabilize BalanceContext's refresh callback
// (which depends on `user`) and cause spurious extra fetches.
const mockUser = { id: "u1" };
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: mockUser }),
}));

vi.mock("@/context/RegionContext", () => ({
  useRegion: () => ({ current: "najaf" }),
}));

vi.mock("@/api/balance", () => ({
  getMyBalance: vi.fn(),
}));

/** Stands in for the navbar pill: a read-only display, elsewhere in the tree
 * from whoever triggers the refresh. */
function BalanceReadout({ testId }: { testId: string }) {
  const { balance } = useBalance();
  return <div data-testid={testId}>{balance ?? "loading"}</div>;
}

/** Stands in for the Transfer Money page: the thing that actually calls
 * refresh() after a successful send. */
function RefreshTrigger() {
  const { refresh } = useBalance();
  return <button onClick={() => refresh()}>refresh</button>;
}

beforeEach(() => {
  vi.mocked(getMyBalance).mockReset();
});

describe("BalanceContext", () => {
  it("propagates a refresh() to every consumer immediately, without a remount", async () => {
    vi.mocked(getMyBalance)
      .mockResolvedValueOnce({ balance: 10_000, total_received: 10_000, total_spent: 0, transactions: [] })
      .mockResolvedValueOnce({ balance: 7_500, total_received: 10_000, total_spent: 2_500, transactions: [] });

    render(
      <BalanceProvider>
        <BalanceReadout testId="navbar-balance" />
        <BalanceReadout testId="transfer-page-balance" />
        <RefreshTrigger />
      </BalanceProvider>
    );

    // Initial fetch on mount lands in both displays -- they share one state.
    await waitFor(() => expect(screen.getByTestId("navbar-balance")).toHaveTextContent("10000"));
    expect(screen.getByTestId("transfer-page-balance")).toHaveTextContent("10000");

    // Simulate what TransferMoneyPage does right after a successful send.
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    // Both displays update together -- this is the fix: no page reload, and
    // no need for the component that shows the balance to be the one that
    // triggered the change.
    await waitFor(() => expect(screen.getByTestId("navbar-balance")).toHaveTextContent("7500"));
    expect(screen.getByTestId("transfer-page-balance")).toHaveTextContent("7500");

    expect(getMyBalance).toHaveBeenCalledTimes(2);
  });
});
