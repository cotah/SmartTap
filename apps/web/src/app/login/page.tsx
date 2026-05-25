import { LoginForm } from "./login-form";

interface PageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

export default async function LoginPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const next = params.next ?? "/dashboard";

  return (
    <main className="container flex min-h-dvh items-center justify-center py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="text-xs tracking-[0.3em] text-brand-green">SMARTTAP</p>
          <h1 className="font-display text-3xl">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">For business owners</p>
        </div>

        {params.error === "auth_callback_failed" ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            Sign-in link expired or invalid. Try again.
          </p>
        ) : null}

        <LoginForm next={next} />
      </div>
    </main>
  );
}
