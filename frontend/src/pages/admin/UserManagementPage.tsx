import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteUser, listUsers, updateUser } from "@/api/users";
import type { User } from "@/types";
import { DataTable, type Column } from "@/components/admin/DataTable";
import { Avatar } from "@/components/common/Avatar";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { formatIQD, formatDate } from "@/utils/assets";
import { ApiRequestError } from "@/api/client";

export function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<User | null>(null);
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
    { key: "role", header: "Role", render: (u) => <Badge color={u.role === "admin" ? "blue" : "zinc"}>{u.role}</Badge> },
    { key: "balance", header: "Balance", render: (u) => <span className="font-medium">{formatIQD(u.balance)}</span> },
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
          <Button
            variant="ghost"
            className={`px-2.5 py-1.5 text-xs ${u.is_active ? "text-red-600 hover:bg-red-50" : "text-green-700 hover:bg-green-50"}`}
            isLoading={busyId === u.id}
            onClick={() => toggleActive(u)}
          >
            {u.is_active ? "Deactivate" : "Activate"}
          </Button>
          {u.id !== currentAdmin?.id && (
            <Button variant="ghost" className="px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50" onClick={() => setPendingDelete(u)}>
              Delete
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
    </div>
  );
}
