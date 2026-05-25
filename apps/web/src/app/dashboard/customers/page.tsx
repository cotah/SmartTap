import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { CustomerListFilter, CustomerListSort } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { CustomersTable } from "./customers-table";
import { ExportButton } from "./export-button";

const PAGE_SIZE = 20;

const FILTERS: CustomerListFilter[] = ["all", "active", "at_risk", "has_reward"];
const SORTS: CustomerListSort[] = ["recent", "visits", "stamps"];

interface PageProps {
  searchParams: Promise<{
    q?: string;
    f?: string;
    s?: string;
    p?: string;
  }>;
}

function parseFilter(value: string | undefined): CustomerListFilter {
  return FILTERS.includes(value as CustomerListFilter)
    ? (value as CustomerListFilter)
    : "all";
}

function parseSort(value: string | undefined): CustomerListSort {
  return SORTS.includes(value as CustomerListSort)
    ? (value as CustomerListSort)
    : "recent";
}

function parsePage(value: string | undefined): number {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 1) return 1;
  return Math.min(Math.floor(n), 10_000);
}

export default async function CustomersPage({ searchParams }: PageProps) {
  await getDashboardContext();
  const sp = await searchParams;

  const search = (sp.q ?? "").trim();
  const filter = parseFilter(sp.f);
  const sort = parseSort(sp.s);
  const page = parsePage(sp.p);

  const api = getAuthApiClient();
  const result = await api.listCustomers({
    search: search || undefined,
    filter,
    sort,
    page,
    limit: PAGE_SIZE,
  });

  return (
    <main className="space-y-6">
      <header className="flex flex-col items-start justify-between gap-3 md:flex-row md:items-end">
        <div>
          <p className="text-sm text-brand-black/60">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / Customers
          </p>
          <h1 className="font-display text-3xl">Customers</h1>
          <p className="mt-1 text-sm text-brand-black/60">
            {result.total} total · showing {result.items.length}
          </p>
        </div>
        <ExportButton search={search} filter={filter} sort={sort} />
      </header>

      <CustomersTable
        initialSearch={search}
        filter={filter}
        sort={sort}
        page={page}
        pageSize={PAGE_SIZE}
        total={result.total}
        items={result.items}
      />
    </main>
  );
}
