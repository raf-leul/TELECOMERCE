import { fetchAdminOrders } from "@/lib/api/admin";
import { formatPrice } from "@/lib/api/client";
import { updateOrderStatus } from "@/app/admin/actions";

const ALL_STATUSES = [
  "pending_payment",
  "paid",
  "processing",
  "packed",
  "shipped",
  "delivered",
  "cancelled",
  "refunded",
];

export default async function AdminOrdersPage() {
  let orders;
  let loadError: string | null = null;

  try {
    orders = await fetchAdminOrders();
  } catch {
    loadError = "Couldn't load orders right now. Is apps/api running?";
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900">Orders</h1>

      {loadError && (
        <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </p>
      )}

      {orders && orders.length === 0 && (
        <p className="text-sm text-zinc-600">No orders yet.</p>
      )}

      {orders && orders.length > 0 && (
        <table className="w-full overflow-hidden rounded-lg border border-zinc-200 bg-white text-sm">
          <thead className="bg-zinc-50 text-left text-zinc-500">
            <tr>
              <th className="px-4 py-2">Order</th>
              <th className="px-4 py-2">Subtotal</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Update</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id} className="border-t border-zinc-100">
                <td className="px-4 py-2 font-mono text-xs text-zinc-500">
                  {order.id.slice(0, 8)}
                </td>
                <td className="px-4 py-2 text-zinc-600">
                  {formatPrice(order.subtotal_cents)}
                </td>
                <td className="px-4 py-2 text-zinc-900">{order.status}</td>
                <td className="px-4 py-2">
                  <form
                    action={updateOrderStatus.bind(null, order.id)}
                    className="flex items-center gap-2"
                  >
                    <select
                      name="status"
                      defaultValue={order.status}
                      className="rounded-md border border-zinc-300 px-2 py-1 text-xs"
                    >
                      {ALL_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <button
                      type="submit"
                      className="rounded-md bg-zinc-900 px-2 py-1 text-xs text-white"
                    >
                      Update
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="mt-4 text-xs text-zinc-500">
        Note: only transitions valid per the order state machine (e.g.
        pending_payment → paid) will succeed — an invalid transition shows
        an error from the API rather than silently applying.
      </p>
    </div>
  );
}
