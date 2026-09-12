"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

function apiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${base}${path}`;
}

async function getAccessToken(): Promise<string> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getSession();
  if (!data.session?.access_token) {
    throw new Error("Not authenticated.");
  }
  return data.session.access_token;
}

export async function toggleProductActive(
  productId: string,
  currentlyActive: boolean
): Promise<void> {
  const token = await getAccessToken();

  const response = await fetch(apiUrl(`/products/${productId}`), {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ is_active: !currentlyActive }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update product (status ${response.status}).`);
  }

  revalidatePath("/admin/products");
}

export async function deleteProduct(productId: string): Promise<void> {
  const token = await getAccessToken();

  const response = await fetch(apiUrl(`/products/${productId}`), {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete product (status ${response.status}).`);
  }

  revalidatePath("/admin/products");
}

export async function updateOrderStatus(
  orderId: string,
  formData: FormData
): Promise<void> {
  const newStatus = String(formData.get("status") ?? "");
  const token = await getAccessToken();

  const response = await fetch(apiUrl(`/orders/${orderId}/status`), {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status: newStatus }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail?.error?.message ?? `status ${response.status}`;
    throw new Error(`Failed to update order: ${message}`);
  }

  revalidatePath("/admin/orders");
}
