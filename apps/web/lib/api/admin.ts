import { createClient } from "@/lib/supabase/server";

export type AdminProduct = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_cents: number;
  is_active: boolean;
  category_id: string | null;
};

export type AdminOrder = {
  id: string;
  user_id: string | null;
  status: string;
  subtotal_cents: number;
  created_at: string;
};

export type AdminOverview = {
  total_orders: number;
  orders_by_status: { status: string; count: number }[];
  revenue_cents: number;
  low_stock_products: {
    product_id: string;
    product_name: string;
    quantity_available: number;
  }[];
};

function apiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}

/**
 * Gets the raw access token string to forward as a Bearer header to
 * apps/api. This does NOT re-derive trust from it directly — apps/api's
 * own JWT verification (Stage 3) independently re-validates the token's
 * signature against Supabase's JWKS. The admin route's actual
 * authorization decision already happened in app/admin/layout.tsx via
 * getClaims(); this is purely about obtaining the token string to pass
 * along.
 */
async function getAccessToken(): Promise<string | null> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function authedFetch(path: string): Promise<Response> {
  const token = await getAccessToken();
  return fetch(apiUrl(path), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
}

export async function fetchAdminOverview(): Promise<AdminOverview> {
  const response = await authedFetch("/admin/overview");
  if (!response.ok) {
    throw new Error(`Failed to load admin overview (status ${response.status})`);
  }
  return response.json();
}

export async function fetchAdminProducts(): Promise<AdminProduct[]> {
  const response = await authedFetch("/admin/products");
  if (!response.ok) {
    throw new Error(`Failed to load admin products (status ${response.status})`);
  }
  return response.json();
}

export async function fetchAdminOrders(): Promise<AdminOrder[]> {
  const response = await authedFetch("/admin/orders");
  if (!response.ok) {
    throw new Error(`Failed to load admin orders (status ${response.status})`);
  }
  return response.json();
}
