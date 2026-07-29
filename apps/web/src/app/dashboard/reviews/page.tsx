import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { ManualReplyCard } from "./manual-reply-card";
import { ReviewSummary } from "./review-summary";
import { ReviewsClient } from "./reviews-client";

export default async function ReviewsPage() {
  const ctx = await getDashboardContext();
  const api = getAuthApiClient();
  const [{ items }, stats, googleStatus] = await Promise.all([
    api.listReviews("pending"),
    api.getReviewStats(),
    api.getGoogleStatus(),
  ]);

  return (
    <main className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-electric-text-muted">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / Reviews
          </p>
          <h1 className="font-display text-3xl">Google reviews</h1>
          <p className="mt-1 text-sm text-electric-text-muted">
            AI-drafted replies waiting for your approval. Nothing is posted to
            Google until you publish it.
          </p>
        </div>
      </header>

      <ReviewSummary stats={stats} />

      <ManualReplyCard
        tenants={ctx.tenants.map((t) => ({ id: t.id, name: t.name }))}
        activeTenantId={ctx.tenant.id}
      />

      <ReviewsClient reviews={items} googleStatus={googleStatus} />
    </main>
  );
}
