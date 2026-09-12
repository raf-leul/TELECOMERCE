import { fetchAdminProducts } from "@/lib/api/admin";
import { formatPrice } from "@/lib/api/client";
import { deleteProduct, toggleProductActive } from "@/app/admin/actions";

export default async function AdminProductsPage() {
  let products;
  let loadError: string | null = null;

  try {
    products = await fetchAdminProducts();
  } catch {
    loadError = "Couldn't load products right now. Is apps/api running?";
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">Products</h1>

      {loadError && (
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </p>
      )}

      {products && products.length === 0 && (
        <p className="text-sm text-zinc-600">
          No products yet — create one via the API (admin product
          creation UI is planned for a future stage).
        </p>
      )}

      {products && products.length > 0 && (
        <table className="w-full overflow-hidden rounded-lg border border-zinc-200 bg-white text-sm">
          <thead className="bg-zinc-50 text-left text-zinc-500">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Price</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.id} className="border-t border-zinc-100">
                <td className="px-4 py-2 text-zinc-900">{product.name}</td>
                <td className="px-4 py-2 text-zinc-600">
                  {formatPrice(product.price_cents)}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={
                      product.is_active
                        ? "rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
                        : "rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600"
                    }
                  >
                    {product.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <form
                    action={toggleProductActive.bind(
                      null,
                      product.id,
                      product.is_active
                    )}
                    className="inline"
                  >
                    <button
                      type="submit"
                      className="mr-3 text-xs text-zinc-700 underline"
                    >
                      {product.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </form>
                  <form
                    action={deleteProduct.bind(null, product.id)}
                    className="inline"
                  >
                    <button type="submit" className="text-xs text-red-600 underline">
                      Delete
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
