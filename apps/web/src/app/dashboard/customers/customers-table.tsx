"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type ChangeEvent, useEffect, useRef, useState, useTransition } from "react";

import type {
  CustomerListFilter,
  CustomerListItem,
  CustomerListSort,
} from "@/lib/api";

interface Props {
  initialSearch: string;
  filter: CustomerListFilter;
  sort: CustomerListSort;
  page: number;
  pageSize: number;
  total: number;
  items: CustomerListItem[];
}

const FILTER_LABELS: Record<CustomerListFilter, string> = {
  all: "All",
  active: "Active",
  at_risk: "At risk",
  has_reward: "Reward ready",
};

const SORT_LABELS: Record<CustomerListSort, string> = {
  recent: "Most recent",
  visits: "Most visits",
  stamps: "Most stamps",
};

export function CustomersTable({
  initialSearch,
  filter,
  sort,
  page,
  pageSize,
  total,
  items,
}: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [searchInput, setSearchInput] = useState(initialSearch);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep input in sync if URL changes (e.g. browser back).
  useEffect(() => {
    setSearchInput(initialSearch);
  }, [initialSearch]);

  function navigate(next: URLSearchParams) {
    const qs = next.toString();
    startTransition(() => {
      router.push(qs ? `?${qs}` : "?");
    });
  }

  function setParam(key: string, value: string | null, resetPage = true): void {
    const next = new URLSearchParams(searchParams?.toString() ?? "");
    if (value === null || value === "") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    if (resetPage) next.delete("p");
    navigate(next);
  }

  function onSearchChange(e: ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setParam("q", value.trim() || null);
    }, 300);
  }

  function onFilterChange(next: CustomerListFilter) {
    setParam("f", next === "all" ? null : next);
  }

  function onSortChange(e: ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value as CustomerListSort;
    setParam("s", next === "recent" ? null : next);
  }

  function goToPage(next: number) {
    setParam("p", next === 1 ? null : String(next), false);
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <input
          type="search"
          value={searchInput}
          onChange={onSearchChange}
          placeholder="Search by name or phone"
          className="w-full rounded-lg border border-brand-black/20 px-3 py-2 text-sm outline-none focus:border-brand-green md:max-w-xs"
        />
        <div className="flex items-center gap-2">
          <label className="text-xs uppercase tracking-wide text-brand-black/60">
            Sort
          </label>
          <select
            value={sort}
            onChange={onSortChange}
            className="rounded-lg border border-brand-black/20 px-3 py-2 text-sm"
          >
            {(Object.keys(SORT_LABELS) as CustomerListSort[]).map((key) => (
              <option key={key} value={key}>
                {SORT_LABELS[key]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter customers">
        {(Object.keys(FILTER_LABELS) as CustomerListFilter[]).map((key) => {
          const active = key === filter;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onFilterChange(key)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                active
                  ? "border-brand-green bg-brand-green text-brand-off-white"
                  : "border-brand-black/20 bg-white text-brand-black/70 hover:border-brand-green"
              }`}
            >
              {FILTER_LABELS[key]}
            </button>
          );
        })}
      </div>

      {items.length === 0 ? (
        <EmptyState filter={filter} hasSearch={Boolean(initialSearch)} />
      ) : (
        <>
          <DesktopTable items={items} />
          <MobileCards items={items} />
        </>
      )}

      <Pagination
        page={page}
        totalPages={totalPages}
        hasPrev={hasPrev}
        hasNext={hasNext}
        pending={pending}
        onPrev={() => goToPage(page - 1)}
        onNext={() => goToPage(page + 1)}
      />
    </section>
  );
}

function DesktopTable({ items }: { items: CustomerListItem[] }) {
  return (
    <div className="hidden overflow-hidden rounded-2xl border border-brand-black/10 bg-white shadow-sm md:block">
      <table className="w-full text-sm">
        <thead className="bg-brand-off-white text-left text-xs uppercase tracking-wide text-brand-black/60">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Phone</th>
            <th className="px-4 py-3 text-right">Stamps</th>
            <th className="px-4 py-3 text-right">Visits</th>
            <th className="px-4 py-3">Last visit</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-black/10">
          {items.map((item) => (
            <tr key={item.id}>
              <td className="px-4 py-3 font-medium">{item.name || "—"}</td>
              <td className="px-4 py-3 text-brand-black/70">{item.phone || "—"}</td>
              <td className="px-4 py-3 text-right">{item.current_stamps}</td>
              <td className="px-4 py-3 text-right">{item.total_visits}</td>
              <td className="px-4 py-3 text-brand-black/70">
                {formatRelative(item.last_visit_at)}
              </td>
              <td className="px-4 py-3 text-right">
                {item.has_reward_ready ? <RewardBadge /> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MobileCards({ items }: { items: CustomerListItem[] }) {
  return (
    <ul className="space-y-2 md:hidden">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-2xl border border-brand-black/10 bg-white p-4 shadow-sm"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium">{item.name || "Unnamed"}</p>
              <p className="text-xs text-brand-black/60">{item.phone || "no phone"}</p>
            </div>
            {item.has_reward_ready ? <RewardBadge /> : null}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-brand-black/70">
            <span>
              <strong className="text-brand-black">{item.current_stamps}</strong> stamps
            </span>
            <span>
              <strong className="text-brand-black">{item.total_visits}</strong> visits
            </span>
            <span>{formatRelative(item.last_visit_at)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function RewardBadge() {
  return (
    <span className="rounded-full bg-brand-amber/15 px-2 py-0.5 text-xs font-semibold text-brand-amber">
      Reward ready
    </span>
  );
}

function EmptyState({
  filter,
  hasSearch,
}: {
  filter: CustomerListFilter;
  hasSearch: boolean;
}) {
  let title = "No customers yet";
  let body = "Spread your SmartTap stand around the shop and watch them roll in.";
  if (hasSearch) {
    title = "No matches";
    body = "Try a different name or phone number.";
  } else if (filter === "active") {
    title = "Nobody active this month";
    body = "Active means visited in the last 30 days.";
  } else if (filter === "at_risk") {
    title = "Nobody at risk";
    body = "Everyone has visited in the last 30 days — well done.";
  } else if (filter === "has_reward") {
    title = "No rewards ready";
    body = "When customers hit your stamp threshold they show up here.";
  }
  return (
    <div className="rounded-2xl border border-dashed border-brand-black/20 bg-white p-8 text-center">
      <p className="font-display text-lg">{title}</p>
      <p className="mt-1 text-sm text-brand-black/60">{body}</p>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  hasPrev,
  hasNext,
  pending,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
  pending: boolean;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between text-sm">
      <button
        type="button"
        onClick={onPrev}
        disabled={!hasPrev || pending}
        className="rounded-full border border-brand-black/20 px-4 py-1.5 disabled:opacity-40"
      >
        ← Prev
      </button>
      <span className="text-brand-black/60">
        Page {page} of {totalPages}
      </span>
      <button
        type="button"
        onClick={onNext}
        disabled={!hasNext || pending}
        className="rounded-full border border-brand-black/20 px-4 py-1.5 disabled:opacity-40"
      >
        Next →
      </button>
    </div>
  );
}

function formatRelative(iso: string | null): string {
  if (!iso) return "never";
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  if (Number.isNaN(diffMs)) return "—";
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days < 0) return "—";
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}
