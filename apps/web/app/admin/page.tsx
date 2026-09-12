import { fetchAdminOverview } from "@/lib/api/admin";
import { formatPrice } from "@/lib/api/client";

export default async function AdminOverviewPage() {
  let overview;
  let loadError: string | null = null;

  try {
    overview = await fetchAdminOverview();
  } catch {
    loadError = "Couldn't load the overview right now. Is apps/api running?";
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">Overview</h1>

      {loadError && (
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </p>
      )}

      {overview && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="text-sm text-zinc-500">Total Orders</p>
            <p className="mt-1 text-2xl font-semibold text-zinc-900">
              {overview.total_orders}
            </p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="text-sm text-zinc-500">Revenue</p>
            <p className="mt-1 text-2xl font-semibold text-zinc-900">
              {formatPrice(overview.revenue_cents)}
            </p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="text-sm text-zinc-500">Low Stock Items</p>
            <p className="mt-1 text-2xl font-semibold text-zinc-900">
              {overview.low_stock_products.length}
            </p>
          </div>

          <div className="col-span-full rounded-lg border border-zinc-200 bg-white p-4">
            <p className="mb-2 text-sm font-medium text-zinc-700">
              Orders by Status
            </p>
            <ul className="flex flex-wrap gap-3 text-sm text-zinc-600">
              {overview.orders_by_status.map((row) => (
                <li
                  key={row.status}
                  className="rounded-full bg-zinc-100 px-3 py-1"
                >
                  {row.status}: {row.count}
                </li>
              ))}
            </ul>
          </div>

          {overview.low_stock_products.length > 0 && (
            <div className="col-span-full rounded-lg border border-zinc-200 bg-white p-4">
              <p className="mb-2 text-sm font-medium text-zinc-700">
                Low Stock Products
              </p>
              <ul className="text-sm text-zinc-600">
                {overview.low_stock_products.map((p) => (
                  <li key={p.product_id}>
                    {p.product_name} — {p.quantity_available} left
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
