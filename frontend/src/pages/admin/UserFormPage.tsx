import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getUser } from "@/api/users";
import type { User } from "@/types";
import { UserForm } from "@/components/admin/UserForm";
import { Skeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";

export function UserFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    getUser(id)
      .then(setUser)
      .catch(() => setError("Could not load user"))
      .finally(() => setIsLoading(false));
  }, [id]);

  return (
    <div>
      <Link to="/admin/users" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-800">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to users
      </Link>
      <h1 className="mb-6 text-xl font-bold text-zinc-900">{isEdit ? "Edit User" : "Create User"}</h1>

      {isLoading ? <Skeleton className="mx-auto h-96 max-w-lg" /> : error ? <ErrorState message={error} /> : <UserForm existingUser={user ?? undefined} />}
    </div>
  );
}
