"use client";

import { useState, useTransition } from "react";

import type { CustomerListFilter, CustomerListSort } from "@/lib/api";

import { exportCustomersAction } from "./actions";

interface Props {
  search: string;
  filter: CustomerListFilter;
  sort: CustomerListSort;
}

export function ExportButton({ search, filter, sort }: Props) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function onClick() {
    setError(null);
    startTransition(async () => {
      const result = await exportCustomersAction({
        search: search || undefined,
        filter,
        sort,
      });
      if (!result.ok) {
        setError(result.message);
        return;
      }
      const blob = new Blob([result.csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={onClick}
        disabled={pending}
        className="rounded-full border border-brand-black/20 px-4 py-1.5 text-sm font-semibold hover:border-brand-green disabled:opacity-60"
      >
        {pending ? "Exporting…" : "Export CSV"}
      </button>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
