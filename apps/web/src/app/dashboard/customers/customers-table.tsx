"use client";

import { Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  type ChangeEvent,
  useEffect,
  useRef,
  useState,
  useTransition,
} from "react";

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
  stampsForReward: number;
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

type Status = "reward_ready" | "at_risk" | "new" | "regular";

interface StatusStyle {
  label: string;
  className: string;
}

const STATUS_STYLES: Record<Status, StatusStyle> = {
  reward_ready: {
    label: "Reward ready",
    className: "bg-electric-cyan/15 text-electric-cyan",
  },
  at_risk: {
    label: "At risk",
    className: "bg-red-500/15 text-red-300",
  },
  new: {
    label: "New",
    className: "bg-electric-surface-2 text-electric-text-muted",
  },
  regular: {
    label: "Regular",
    className: "bg-electric-surface-2 text-electric-text",
  },
};

function deriveStatus(item: CustomerListItem): Status {
  if (item.has_reward_ready) return "reward_ready";
  if (isAtRisk(item.last_visit_at)) return "at_risk";
  if (item.total_visits <= 1) return "new";
  return "regular";
}

function isAtRisk(lastVisitIso: string | null): boolean {
  if (!lastVisitIso) return true;
  const date = new Date(lastVisitIso);
  if (Number.isNaN(date.getTime())) return false;
  const diffDays = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
  return diffDays >= 30;
}

export function CustomersTable({
  initialSearch,
  filter,
  sort,
  page,
  pageSize,
  total,
  items,
  stampsForReward,
}: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [searchInput, setSearchInput] = useState(initialSearch);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    <section className="space-y-6">
      {/* Search + Sort row */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full max-w-md">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-electric-text-muted">
            <Search className="h-5 w-5" aria-hidden="true" />
          </span>
          <input
            type="search"
            value={searchInput}
            onChange={onSearchChange}
            placeholder="Search by name or phone…"
            className="w-full rounded-lg border border-electric-border bg-electric-surface py-3 pl-10 pr-4 text-sm text-electric-text outline-none transition-colors placeholder:text-electric-text-muted/60 focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30"
          />
        </div>
        <div className="flex items-center gap-2">
          <label
            htmlFor="customers-sort"
            className="text-xs font-bold uppercase tracking-wider text-electric-text-muted"
          >
            Sort
          </label>
          <select
            id="customers-sort"
            value={sort}
            onChange={onSortChange}
            className="rounded-lg border border-electric-border bg-electric-surface px-3 py-2.5 text-sm text-electric-text focus:border-electric-cyan focus:outline-none focus:ring-2 focus:ring-electric-cyan/30"
          >
            {(Object.keys(SORT_LABELS) as CustomerListSort[]).map((key) => (
              <option key={key} value={key}>
                {SORT_LABELS[key]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Filter pills */}
      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Filter customers"
      >
        {(Object.keys(FILTER_LABELS) as CustomerListFilter[]).map((key) => {
          const active = key === filter;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onFilterChange(key)}
              className={`rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors ${
                active
                  ? "bg-electric-cyan text-electric-bg shadow-[0_0_14px_rgba(0,212,255,0.35)]"
                  : "bg-electric-surface text-electric-text-muted hover:bg-electric-surface-2 hover:text-electric-cyan"
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
        <div className="overflow-hidden rounded-xl border border-electric-border bg-electric-surface">
          <DesktopTable items={items} stampsForReward={stampsForReward} />
          <MobileCards items={items} stampsForReward={stampsForReward} />
        </div>
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

function DesktopTable({
  items,
  stampsForReward,
}: {
  items: CustomerListItem[];
  stampsForReward: number;
}) {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-left">
        <thead className="border-b border-electric-border bg-electric-surface-2">
          <tr>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Name
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Phone
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Stamps
            </th>
            <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Visits
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Last visit
            </th>
            <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-electric-border">
          {items.map((item) => (
            <tr
              key={item.id}
              className="transition-colors hover:bg-electric-surface-2"
            >
              <td className="px-6 py-4 text-sm font-medium text-electric-text">
                {item.name || "—"}
              </td>
              <td className="px-6 py-4 text-sm text-electric-text-muted">
                {item.phone || "—"}
              </td>
              <td className="px-6 py-4">
                <StampProgress
                  current={item.current_stamps}
                  total={stampsForReward}
                  ready={item.has_reward_ready}
                />
              </td>
              <td className="px-6 py-4 text-right text-sm text-electric-text">
                {item.total_visits}
              </td>
              <td className="px-6 py-4 text-sm text-electric-text-muted">
                {formatRelative(item.last_visit_at)}
              </td>
              <td className="px-6 py-4">
                <StatusBadge status={deriveStatus(item)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MobileCards({
  items,
  stampsForReward,
}: {
  items: CustomerListItem[];
  stampsForReward: number;
}) {
  return (
    <ul className="divide-y divide-electric-border md:hidden">
      {items.map((item) => (
        <li key={item.id} className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-medium text-electric-text">
                {item.name || "Unnamed"}
              </p>
              <p className="text-xs text-electric-text-muted">
                {item.phone || "no phone"}
              </p>
            </div>
            <StatusBadge status={deriveStatus(item)} />
          </div>
          <StampProgress
            current={item.current_stamps}
            total={stampsForReward}
            ready={item.has_reward_ready}
          />
          <div className="flex items-center justify-between text-xs text-electric-text-muted">
            <span>
              <strong className="text-electric-text">{item.total_visits}</strong>{" "}
              visits
            </span>
            <span>{formatRelative(item.last_visit_at)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function StampProgress({
  current,
  total,
  ready,
}: {
  current: number;
  total: number;
  ready: boolean;
}) {
  const safeTotal = Math.max(total, 1);
  const pct = Math.min(100, Math.max(0, (current / safeTotal) * 100));
  const barColor = ready ? "bg-electric-cyan" : "bg-electric-cyan/50";
  const valueColor = ready ? "text-electric-cyan" : "text-electric-text";

  return (
    <div className="flex items-center gap-2">
      <span className={`text-sm font-bold tabular-nums ${valueColor}`}>
        {current}/{total}
      </span>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-electric-surface-2">
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const style = STATUS_STYLES[status];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${style.className}`}
    >
      {style.label}
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
    <div className="rounded-xl border border-dashed border-electric-border bg-electric-surface p-10 text-center">
      <p className="font-display text-xl font-semibold text-electric-cyan">{title}</p>
      <p className="mt-2 text-sm text-electric-text-muted">{body}</p>
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
        className="rounded-lg border border-electric-border bg-electric-surface px-4 py-2 font-medium text-electric-text transition-colors hover:border-electric-cyan hover:text-electric-cyan disabled:opacity-40"
      >
        ← Prev
      </button>
      <span className="text-electric-text-muted">
        Page {page} of {totalPages}
      </span>
      <button
        type="button"
        onClick={onNext}
        disabled={!hasNext || pending}
        className="rounded-lg border border-electric-border bg-electric-surface px-4 py-2 font-medium text-electric-text transition-colors hover:border-electric-cyan hover:text-electric-cyan disabled:opacity-40"
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
