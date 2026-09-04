import Link from "next/link";
import { fetchProducts, formatPrice } from "@/lib/api/client";

export default async function ShopPage() {
  let products;
  let loadError: string | null = null;

  try {
    products = await fetchProducts();
  } catch {
    loadError =
      "Couldn't load products right now. Make sure apps/api is running (see docs/DEVELOPMENT_LOG.md).";
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="mb-8 text-3xl font-semibold text-zinc-900">Shop</h1>

      {loadError && (
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </p>
      )}

      {products && products.length === 0 && (
        <p className="text-sm text-zinc-600">No products yet.</p>
      )}

      {products && products.length > 0 && (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {products.map((product) => (
            <li
              key={product.id}
              className="rounded-lg border border-zinc-200 p-4"
            >
              <Link
                href={`/products/${product.slug}`}
                className="font-medium text-zinc-900 hover:underline"
              >
                {product.name}
              </Link>
              <p className="mt-1 text-sm text-zinc-600">
                {formatPrice(product.price_cents)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
