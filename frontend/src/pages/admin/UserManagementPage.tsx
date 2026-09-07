import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteUser, listUsers, permanentlyDeleteUser, setUserRegions, updateUser } from "@/api/users";
import type { Region, User } from "@/types";
import { DataTable, type Column } from "@/components/admin/DataTable";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PermanentDeleteDialog } from "@/components/admin/PermanentDeleteDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { formatDate } from "@/utils/assets";
import { REGIONS, isSuperAdmin, regionBadgeColor, regionLabel, roleBadgeColor, roleLabel } from "@/utils/roles";
import { ApiRequestError } from "@/api/client";

export function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<User | null>(null);
  const [pendingPurge, setPendingPurge] = useState<User | null>(null);
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user: currentAdmin } = useAuth();

  const load = () => {
    setIsLoading(true);
    setError(null);
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Could not load users"))
      .finally(() => setIsLoading(false));
  };

  useEffect(load, []);

  const toggleActive = async (user: User) => {
    setBusyId(user.id);
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      showToast(updated.is_active ? "User activated" : "User deactivated", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not update user", "error");
    } finally {
      setBusyId(null);
    }
  };

  // Mirrors the backend rules (core/deps.require_super_admin and
  // user_service._assert_can_assign_role). Hiding these buttons is a courtesy;
  // the API rejects the calls regardless of what the UI renders.
  const canManageRoles = isSuperAdmin(currentAdmin);

  const changeRole = async (user: User, role: "admin" | "customer") => {
    setBusyId(user.id);
    try {
      const updated = await updateUser(user.id, { role });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      showToast(role === "admin" ? `${user.username} promoted to Admin` : `${user.username} demoted to User`, "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not change role", "error");
    } finally {
      setBusyId(null);
    }
  };

  /** Toggling a region grants or revokes access. It never moves money or
   * history — the backend keeps each region's wallet and ledger separate. */
  const toggleRegion = async (user: User, region: Region) => {
    const next = user.regions.includes(region)
      ? user.regions.filter((r) => r !== region)
      : [...user.regions, region];
    if (next.length === 0) {
      showToast("An account must belong to at least one region", "error");
      return;
    }
    setBusyId(user.id);
    try {
      const updated = await setUserRegions(user.id, next);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      showToast(`${user.username}: ${updated.regions.map(regionLabel).join(", ")}`, "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not change region access", "error");
    } finally {
      setBusyId(null);
    }
  };

  const handlePermanentDelete = async (confirmUsername: string) => {
    if (!pendingPurge) return;
    try {
      await permanentlyDeleteUser(pendingPurge.id, confirmUsername);
      setUsers((prev) => prev.filter((u) => u.id !== pendingPurge.id));
      showToast(`${pendingPurge.username} permanently deleted`, "success");
      setPendingPurge(null);
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not delete account", "error");
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteUser(pendingDelete.id);
      setUsers((prev) => prev.filter((u) => u.id !== pendingDelete.id));
      showToast("User deleted", "success");
    } catch (err) {
      showToast(err instanceof ApiRequestError ? err.message : "Could not delete user", "error");
    } finally {
      setPendingDelete(null);
    }
  };

  const filtered = users.filter((u) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return u.username.toLowerCase().includes(q) || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
  });

  const columns: Column<User>[] = [
    {
      key: "user",
      header: "User",
      render: (u) => (
        <Link to={`/admin/users/${u.id}`} className="flex items-center gap-3">
          <Avatar src={u.avatar_url} name={u.full_name} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-zinc-900">{u.full_name}</p>
            <p className="truncate text-xs text-zinc-500">@{u.username}</p>
          </div>
        </Link>
      ),
    },
    { key: "email", header: "Email", render: (u) => <span className="text-zinc-600">{u.email}</span> },
    {
      key: "role",
      header: "Role",
      render: (u) => (
        <Badge color={roleBadgeColor(u.role)}>{roleLabel(u.role)}</Badge>
      ),
    },
    {
      key: "region",
      header: "Region",
      render: (u) =>
        canManageRoles && u.role !== "super_admin" ? (
          <div className="flex flex-col gap-1">
            {REGIONS.map((r) => (
              <label key={r} className="flex items-center gap-1.5 text-xs font-medium text-zinc-700">
                <input
                  type="checkbox"
                  checked={u.regions.includes(r)}
                  disabled={busyId === u.id}
                  onChange={() => toggleRegion(u, r)}
                  className="h-3.5 w-3.5 rounded border-zinc-300 text-brand-600 focus:ring-brand-500"
                />
                {regionLabel(r)}
              </label>
            ))}
          </div>
        ) : (
          <span className="flex flex-wrap gap-1">
            {u.regions.length === 0 ? (
              <Badge color="zinc">—</Badge>
            ) : (
              u.regions.map((r) => (
                <Badge key={r} color={regionBadgeColor(r)}>
                  {regionLabel(r)}
                </Badge>
              ))
            )}
          </span>
        ),
    },
    { key: "status", header: "Status", render: (u) => <Badge color={u.is_active ? "green" : "red"}>{u.is_active ? "Active" : "Inactive"}</Badge> },
    { key: "joined", header: "Joined", render: (u) => <span className="text-zinc-500">{formatDate(u.created_at)}</span> },
    {
      key: "actions",
      header: "",
      render: (u) => (
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" className="px-2.5 py-1.5 text-xs" onClick={() => navigate(`/admin/users/${u.id}/edit`)}>
            Edit
          </Button>
          {/* The Super Admin can't be deactivated — doing so would lock the
              protected account out (backend enforces this too). */}
          {u.role !== "super_admin" && (
            <Button
              variant="ghost"
              className={`px-2.5 py-1.5 text-xs ${u.is_active ? "text-red-600 hover:bg-red-50" : "text-green-700 hover:bg-green-50"}`}
              isLoading={busyId === u.id}
              onClick={() => toggleActive(u)}
            >
              {u.is_active ? "Deactivate" : "Activate"}
            </Button>
          )}
          {canManageRoles && u.role === "customer" && (
            <Button variant="ghost" className="px-2.5 py-1.5 text-xs text-brand-600 hover:bg-brand-50" isLoading={busyId === u.id} onClick={() => changeRole(u, "admin")}>
              Promote to Admin
            </Button>
          )}
          {canManageRoles && u.role === "admin" && (
            <Button variant="ghost" className="px-2.5 py-1.5 text-xs text-amber-700 hover:bg-amber-50" isLoading={busyId === u.id} onClick={() => changeRole(u, "customer")}>
              Demote Admin
            </Button>
          )}
          {u.id !== currentAdmin?.id && u.role !== "super_admin" && (
            <Button variant="ghost" className="px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50" onClick={() => setPendingDelete(u)}>
              Delete
            </Button>
          )}
          {canManageRoles && u.id !== currentAdmin?.id && u.role !== "super_admin" && (
            <Button variant="ghost" className="px-2.5 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50" onClick={() => setPendingPurge(u)}>
              Delete Permanently
            </Button>
          )}
        </div>
      ),
      className: "text-right",
    },
  ];

  return (
    <div>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users..." className="input max-w-xs" />
        <Button onClick={() => navigate("/admin/users/new")}>+ Create user</Button>
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : <DataTable columns={columns} rows={filtered} rowKey={(u) => u.id} isLoading={isLoading} emptyTitle="No users found" />}

      <ConfirmDialog
        isOpen={!!pendingDelete}
        title="Delete user"
        message={`Are you sure you want to delete "${pendingDelete?.full_name}"? This cannot be undone. Users with existing orders or transactions can't be deleted — deactivate them instead.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />

      <PermanentDeleteDialog user={pendingPurge} onConfirm={handlePermanentDelete} onCancel={() => setPendingPurge(null)} />
    </div>
  );
}
