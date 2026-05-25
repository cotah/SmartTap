import { cookies } from "next/headers";

const COOKIE_NAME = "smarttap_magic";
const MAX_AGE_DAYS = 365;

export async function readMagicToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(COOKIE_NAME)?.value ?? null;
}

export async function writeMagicToken(token: string): Promise<void> {
  const jar = await cookies();
  jar.set({
    name: COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * MAX_AGE_DAYS,
  });
}

export async function clearMagicToken(): Promise<void> {
  const jar = await cookies();
  jar.delete(COOKIE_NAME);
}
