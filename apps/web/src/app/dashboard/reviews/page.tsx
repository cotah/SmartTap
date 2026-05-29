import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { ReviewsClient } from "./reviews-client";

export default async function ReviewsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listReviews("pending");

  return (
    <main className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-brand-black/60">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / Reviews
          </p>
          <h1 className="font-display text-3xl">Google reviews</h1>
          <p className="mt-1 text-sm text-brand-black/60">
            AI-drafted replies waiting for your approval. Nothing is posted to
            Google until you publish it.
          </p>
        </div>
      </header>

      <ReviewsClient reviews={items} />
    </main>
  );
}
