"use server";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { CustomerListFilter, CustomerListSort } from "@/lib/api";

export interface ExportInput {
  search?: string;
  filter?: CustomerListFilter;
  sort?: CustomerListSort;
}

export type ExportResult =
  | { ok: true; csv: string; filename: string }
  | { ok: false; message: string };

export async function exportCustomersAction(input: ExportInput): Promise<ExportResult> {
  try {
    const api = getAuthApiClient();
    const csv = await api.exportCustomersCsv({
      search: input.search,
      filter: input.filter,
      sort: input.sort,
    });
    const stamp = new Date().toISOString().slice(0, 10);
    return { ok: true, csv, filename: `smarttap-customers-${stamp}.csv` };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not export." };
    }
    return { ok: false, message: "Could not export. Try again." };
  }
}
