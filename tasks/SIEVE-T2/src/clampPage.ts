export function clampPage(page: number, totalPages: number): number {
  return Math.min(page, totalPages);
}
