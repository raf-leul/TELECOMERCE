import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchProductBySlug, formatPrice } from "@/lib/api/client";

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  let product;
  try {
    product = await fetchProductBySlug(slug);
  } catch {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16">
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          Couldn&apos;t load this product right now. Make sure apps/api is
          running (see docs/DEVELOPMENT_LOG.md).
        </p>
      </div>
    );
  }

  if (!product) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <Link href="/shop" className="text-sm text-zinc-600 hover:underline">
        &larr; Back to shop
      </Link>
      <h1 className="mt-4 text-3xl font-semibold text-zinc-900">
        {product.name}
      </h1>
      <p className="mt-2 text-xl text-zinc-700">
        {formatPrice(product.price_cents)}
      </p>
      {product.description && (
        <p className="mt-6 text-zinc-600">{product.description}</p>
      )}
    </div>
  );
}
