export function canAwardStamp(
  lastStampAt: Date | null,
  rateLimitMinutes: number,
  now: Date = new Date(),
): boolean {
  if (lastStampAt === null) return true;
  if (rateLimitMinutes <= 0) return true;
  const elapsedMinutes = (now.getTime() - lastStampAt.getTime()) / 60_000;
  return elapsedMinutes >= rateLimitMinutes;
}
