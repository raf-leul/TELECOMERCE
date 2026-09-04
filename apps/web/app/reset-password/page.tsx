"use client";

import { useActionState } from "react";
import { updatePassword, type AuthActionState } from "@/app/auth/actions";

export default function ResetPasswordPage() {
  const [state, formAction, pending] = useActionState<
    AuthActionState,
    FormData
  >(updatePassword, undefined);

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">
        Set a new password
      </h1>
      <form action={formAction} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm text-zinc-700">
          New password
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            className="rounded-md border border-zinc-300 px-3 py-2"
          />
        </label>
        {state?.error && (
          <p className="text-sm text-red-600" role="alert">
            {state.error}
          </p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="mt-2 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {pending ? "Saving..." : "Save new password"}
        </button>
      </form>
    </div>
  );
}
