/** Preserve the incoming request stream while replacing only proxy-controlled headers. */
export function authorizedOpenAIRequest(request: Request, apiKey: string): Request {
  const headers = new Headers(request.headers);
  headers.set("authorization", `Bearer ${apiKey}`);
  headers.delete("vercel-sandbox-oidc-token");
  return new Request(request, { headers });
}
