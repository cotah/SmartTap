// Loading state for /dashboard navigations (S5 audit F1). Shown while server
// components fetch, so the screen isn't blank between clicks.
export default function DashboardLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-brand-black/10" />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-2xl border border-brand-black/10 bg-white"
          />
        ))}
      </div>
    </div>
  );
}
