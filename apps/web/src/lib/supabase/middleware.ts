import { NextResponse, type NextRequest } from "next/server";

export function updateSession(_request: NextRequest): NextResponse {
  // Intentionally simple: auth gating happens in dashboard/layout.tsx via
  // requireUser(). Keeping the middleware free of @supabase/ssr session
  // refresh avoids a class of cookie-race bugs we hit in dev with Next 15.5.
  return NextResponse.next();
}
