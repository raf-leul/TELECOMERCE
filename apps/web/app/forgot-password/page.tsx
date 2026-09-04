"use client";

import { Suspense, useActionState, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  requestPasswordReset,
  type AuthActionState,
} from "@/app/auth/actions";

function LinkErrorNotice() {
  const searchParams = useSearchParams();
  const linkError = searchParams.get("error");

  if (!linkError) return null;

  return (
    <p className="mb-4 text-sm text-red-600" role="alert">
      {linkError.replaceAll("+", " ")}
    </p>
  );
}

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);

  const [state, formAction, pending] = useActionState<
    AuthActionState,
    FormData
  >(requestPasswordReset, undefined);

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">
        Reset your password
      </h1>

      <Suspense fallback={null}>
        <LinkErrorNotice />
      </Suspense>

      <form
        action={formAction}
        onSubmit={() => setSubmitted(true)}
        className="flex flex-col gap-4"
      >
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
          {pending ? "Sending..." : "Send reset link"}
        </button>
      </form>

      {submitted && !pending && !state?.error && (
        <p className="mt-4 text-sm text-zinc-600">
          If an account exists for that email, a reset link has been sent.
        </p>
      )}

      <p className="mt-4 text-sm text-zinc-600">
        <Link href="/login" className="underline">
          Back to log in
        </Link>
      </p>
    </div>
  );
}
