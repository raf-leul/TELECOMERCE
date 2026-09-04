"use client";

import { useActionState } from "react";
import Link from "next/link";
import { signIn, type AuthActionState } from "@/app/auth/actions";

export default function LoginPage() {
  const [state, formAction, pending] = useActionState<
    AuthActionState,
    FormData
  >(signIn, undefined);

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">Log in</h1>
      <form action={formAction} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm text-zinc-700">
          Email
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className="rounded-md border border-zinc-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-zinc-700">
          Password
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
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
          {pending ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-zinc-600">
        <Link href="/forgot-password" className="underline">
          Forgot your password?
        </Link>
      </p>
      <p className="mt-2 text-sm text-zinc-600">
        Need an account?{" "}
        <Link href="/register" className="underline">
          Register
        </Link>
      </p>
    </div>
  );
}
