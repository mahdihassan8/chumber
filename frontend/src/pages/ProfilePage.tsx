import { useEffect, useState } from "react";
import { getMyBalance } from "@/api/balance";
import type { Balance } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import { ProfileCard } from "@/components/profile/ProfileCard";
import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";
import { AvatarPicker } from "@/components/profile/AvatarPicker";
import { BalanceDisplay } from "@/components/balance/BalanceDisplay";
import { TransactionList } from "@/components/balance/TransactionList";
import { Skeleton } from "@/components/common/Skeleton";
import { Badge } from "@/components/common/Badge";
import { useAuth } from "@/context/AuthContext";

export function ProfilePage() {
  const { user } = useAuth();
  const [balance, setBalance] = useState<Balance | null>(null);

  useEffect(() => {
    getMyBalance()
      .then(setBalance)
      .catch(() => setBalance(null));
  }, []);

  if (!user) return null;

  return (
    <PageContainer className="max-w-3xl">
      <div className="mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-zinc-900">Profile</h1>
        <Badge color={user.role === "admin" ? "blue" : "zinc"}>{user.role}</Badge>
      </div>

      <div className="space-y-6">
        <section className="card p-6">
          <h2 className="mb-4 font-semibold text-zinc-900">Avatar</h2>
          <AvatarPicker />
        </section>

        <section className="card p-6">
          <h2 className="mb-4 font-semibold text-zinc-900">Account details</h2>
          <ProfileCard />
        </section>

        <section className="card p-6">
          <h2 className="mb-4 font-semibold text-zinc-900">Change password</h2>
          <ChangePasswordForm />
        </section>

        <section>
          <BalanceDisplay balance={user.balance} />
        </section>

        <section className="card p-6">
          <h2 className="mb-2 font-semibold text-zinc-900">Balance history</h2>
          {balance ? <TransactionList transactions={balance.transactions} currency="beans" /> : <Skeleton className="h-24 w-full" />}
        </section>
      </div>
    </PageContainer>
  );
}
