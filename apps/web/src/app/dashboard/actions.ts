"use server";

import { redirect } from "next/navigation";

import { ApiError, getAuthApiClient } from "@/lib/api";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function signOutAction(): Promise<void> {
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();
  redirect("/login");
}

export type DownloadMonthlyReportResult =
  | { ok: true; pdfBase64: string; filename: string }
  | { ok: false; message: string };

export interface DownloadMonthlyReportInput {
  year?: number;
  month?: number;
}

/**
 * Streams the PDF from the backend through this Server Action, returns
 * base64 so the client can rebuild a Blob and save it. Server Actions
 * can't return Blob/File directly; base64 keeps the wire format simple
 * (a ~50KB PDF becomes ~67KB string — negligible at our scale and avoids
 * the need for a separate signed-URL infra).
 */
export async function downloadMonthlyReportAction(
  input: DownloadMonthlyReportInput = {},
): Promise<DownloadMonthlyReportResult> {
  try {
    const api = getAuthApiClient();
    const { blob, filename } = await api.downloadMonthlyReport(input);
    const buf = await blob.arrayBuffer();
    const pdfBase64 = Buffer.from(buf).toString("base64");
    return { ok: true, pdfBase64, filename };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not generate report." };
    }
    return { ok: false, message: "Could not generate report. Try again." };
  }
}
