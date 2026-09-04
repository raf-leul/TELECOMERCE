/**
 * Thin fetch wrapper for apps/api. apps/web deliberately goes through the
 * shared backend for catalog data (not directly to Supabase) — see
 * docs/ARCHITECTURE.md, "one source of truth" — even though these are
 * public reads that Supabase's RLS would also allow directly. This keeps
 * the door open for the Telegram bot (Stage 8) to reuse identical business
 * logic without duplicating it, per the master instructions' core
 * architecture principle.
 */

export type Product = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_cents: number;
  is_active: boolean;
  category_id: string | null;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  parent_category_id: string | null;
};

function apiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}

export async function fetchProducts(): Promise<Product[]> {
  const response = await fetch(apiUrl("/products"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load products (status ${response.status})`);
  }
  return response.json();
}

export async function fetchProductBySlug(slug: string): Promise<Product | null> {
  const response = await fetch(apiUrl(`/products/${encodeURIComponent(slug)}`), {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load product (status ${response.status})`);
  }
  return response.json();
}

export function formatPrice(priceCents: number): string {
  return (priceCents / 100).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}
