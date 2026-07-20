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
  const widthIndex = argumentsList.indexOf("--width");
  const heightIndex = argumentsList.indexOf("--height");
  const width = widthIndex < 0 ? 1280 : Number(argumentsList[widthIndex + 1]);
  const height = heightIndex < 0 ? 900 : Number(argumentsList[heightIndex + 1]);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) {
    throw new Error("--width and --height must be positive integers");
  }
  return { input: path.resolve(input), output: path.resolve(output), width, height };
}

const { input, output, width, height } = parseArguments(process.argv.slice(2));
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width, height } });
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
