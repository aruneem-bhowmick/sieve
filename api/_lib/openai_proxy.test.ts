import { describe, expect, it } from "vitest";

import { authorizedOpenAIRequest } from "./openai_proxy";

describe("authorized OpenAI proxy request", () => {
  it("preserves the request stream while replacing proxy-controlled headers", async () => {
    const request = new Request("https://api.openai.com/v1/responses?stream=true", {
      method: "POST",
      headers: { "content-type": "application/json", "vercel-sandbox-oidc-token": "untrusted" },
      body: JSON.stringify({ model: "gpt-5.6-terra" }),
    });
    const forwarded = authorizedOpenAIRequest(request, "server-key");
    expect(forwarded.url).toBe(request.url);
    expect(forwarded.headers.get("authorization")).toBe("Bearer server-key");
    expect(forwarded.headers.has("vercel-sandbox-oidc-token")).toBe(false);
    await expect(forwarded.text()).resolves.toBe(JSON.stringify({ model: "gpt-5.6-terra" }));
  });
});
