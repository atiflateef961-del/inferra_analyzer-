import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const backendRoot = path.resolve(frontendRoot, "..", "backend");

const scriptText = readFileSync(path.join(frontendRoot, "scripts", "dev.ps1"), "utf8");
const backendScriptText = readFileSync(path.join(backendRoot, "scripts", "dev.ps1"), "utf8");

test("frontend startup script binds to localhost in local mode", () => {
  assert.match(scriptText, /\$hostname = if \(\$Mode -eq "Network"\) \{ "0\.0\.0\.0" \} else \{ "127\.0\.0\.1" \}/);
  assert.match(scriptText, /\$selectedUrl = if \(\$Mode -eq "Network" -and \$networkAddress\) \{ \$networkUrl \} else \{ \$localUrl \}/);
  assert.match(scriptText, /\$nextArguments = @\(\$nextBin, "dev", "--hostname", \$hostname, "--port", "\$port"\)/);
});

test("frontend script selects a LAN URL when running in network mode", () => {
  assert.match(scriptText, /\$networkUrl = if \(\$networkAddress\) \{ "http:\/\/\$networkAddress`\:\$port" \} else \{ "unavailable" \}/);
  assert.match(scriptText, /\$env:BACKEND_URL = \$backendUrl/);
  assert.match(scriptText, /\$backendUrl = if \(\$Mode -eq "Network" -and \$networkAddress\) \{ "http:\/\/\$networkAddress`\:\$backendPort" \} else \{ "http:\/\/127\.0\.0\.1`\:\$backendPort" \}/);
});

test("frontend mode selection opens the selected URL automatically", () => {
  const selectorText = readFileSync(path.join(frontendRoot, "scripts", "dev-select.ps1"), "utf8");
  assert.match(selectorText, /-OpenBrowser/);
  assert.match(scriptText, /Write-Host "Opening browser automatically: \$Url"/);
  assert.match(scriptText, /-ArgumentList @\("--new-window", \$Url\)/);
});

test("backend startup script exposes the LAN host and CORS origins", () => {
  assert.match(backendScriptText, /\$hostname = if \(\$Mode -eq "Network"\) \{ "0\.0\.0\.0" \} else \{ "127\.0\.0\.1" \}/);
  assert.match(backendScriptText, /\$corsOrigins = @\("http:\/\/localhost:3000", "http:\/\/127\.0\.0\.1:3000"\)/);
  assert.match(backendScriptText, /\$corsOrigins \+= "http:\/\/\$networkAddress`:3000"/);
});

test("network config resolves browser-safe backend and origin defaults", async () => {
  const { getDefaultBackendUrl, getFrontendAllowedOrigins } = await import("../lib/network-config.ts");

  const backendUrl = getDefaultBackendUrl();
  const allowedOrigins = getFrontendAllowedOrigins();

  assert.match(backendUrl, /^http:\/\/\d+\.\d+\.\d+\.\d+:8000$/);
  assert.ok(allowedOrigins.includes("http://localhost:3000"));
  assert.ok(allowedOrigins.includes("http://127.0.0.1:3000"));
  assert.ok(allowedOrigins.some((origin) => origin.startsWith("http://") && origin.includes(":3000")));
});
