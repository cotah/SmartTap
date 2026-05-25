const IRISH_PHONE_REGEX = /^\+353[1-9]\d{6,9}$/;

export function isValidIrishPhone(phone: string): boolean {
  return IRISH_PHONE_REGEX.test(phone);
}

export function formatIrishPhone(input: string): string {
  const digits = input.replace(/\D/g, "");
  if (digits.startsWith("353")) return `+${digits}`;
  if (digits.startsWith("0")) return `+353${digits.slice(1)}`;
  return `+353${digits}`;
}
