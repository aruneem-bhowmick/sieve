function normalizeUsername(value: string): string {
  return `@${value.trim().toLowerCase()}`;
}

export function formatUsername(value: string): string {
  return normalizeUsername(value);
}
