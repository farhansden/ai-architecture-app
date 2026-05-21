/** Production API host (Railway). Set NEXT_PUBLIC_API_URL in Vercel. */
export function getApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  return raw.trim().replace(/\/+$/, '');
}
