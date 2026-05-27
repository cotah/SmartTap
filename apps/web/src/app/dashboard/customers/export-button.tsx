"use client";

import { Download } from "lucide-react";
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
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <button
        type="button"
        onClick={onClick}
        disabled={pending}
        className="inline-flex items-center gap-2 rounded-lg border border-brand-green px-5 py-2.5 text-sm font-bold uppercase tracking-wider text-brand-green transition-colors hover:bg-brand-green hover:text-white disabled:opacity-60"
      >
        <Download className="h-4 w-4" aria-hidden="true" />
        {pending ? "Exporting…" : "Export CSV"}
      </button>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
