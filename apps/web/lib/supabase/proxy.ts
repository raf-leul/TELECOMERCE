import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Refreshes the Supabase auth session on every matched request and writes
 * the refreshed cookie onto both the incoming request (so Server
 * Components downstream see it) and the outgoing response (so the browser
 * gets the updated cookie). Called from proxy.ts.
 *
 * Uses getClaims(), never getSession(), to determine auth state here —
 * getSession() reads from storage without re-validating the JWT signature,
 * which is not safe to trust in proxy/middleware code. See
 * https://supabase.com/docs/guides/auth/server-side/creating-a-client
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // This call refreshes the token if needed and validates it against the
  // project's published public keys.
  await supabase.auth.getClaims();

  return supabaseResponse;
}
