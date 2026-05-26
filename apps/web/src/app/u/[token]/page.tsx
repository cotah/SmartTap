import { notFound } from "next/navigation";

import { OptOutView } from "./opt-out-view";

interface PageProps {
  params: Promise<{ token: string }>;
}

// Tokens are URL-safe base64 from secrets.token_urlsafe(24) — ~32 chars,
// alphanumeric plus "-" and "_". Bound length here to avoid handing huge
// strings to the backend.
const TOKEN_RE = /^[A-Za-z0-9_-]{8,128}$/;

export default async function OptOutPage({ params }: PageProps) {
  const { token } = await params;
  if (!TOKEN_RE.test(token)) notFound();

  return (
    <main className="container flex min-h-dvh items-center justify-center px-4 py-8">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-sm">
        <OptOutView token={token} />
      </div>
    </main>
  );
}
