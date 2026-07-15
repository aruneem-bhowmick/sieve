import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

function parseArguments(argumentsList) {
  const inputIndex = argumentsList.indexOf("--input");
  const outputIndex = argumentsList.indexOf("--output");
  if (inputIndex < 0 || outputIndex < 0) {
    throw new Error("usage: --input <html-path> --output <png-path>");
  }
  const input = argumentsList[inputIndex + 1];
  const output = argumentsList[outputIndex + 1];
  if (!input || !output || input.startsWith("http") || output.startsWith("http")) {
    throw new Error("input and output must be local file paths");
  }
  return { input: path.resolve(input), output: path.resolve(output) };
}

const { input, output } = parseArguments(process.argv.slice(2));
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("request", (request) => {
    if (new URL(request.url()).protocol !== "file:") {
      request.abort();
    }
  });
  await page.goto(pathToFileURL(input).href, { waitUntil: "load" });
  await page.screenshot({ path: output });
} finally {
  await browser.close();
}
