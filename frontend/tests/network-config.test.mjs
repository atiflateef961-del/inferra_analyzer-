import assert from "node:assert/strict";
import test from "node:test";

test("network config resolves a LAN-safe backend URL", async () => {
  const { getDefaultBackendUrl } = await import("../lib/network-config.ts");

  assert.match(getDefaultBackendUrl(), /^http:\/\/\d+\.\d+\.\d+\.\d+:8000$/);
});

test("network config exposes localhost and LAN origins", async () => {
  const { getFrontendAllowedOrigins } = await import("../lib/network-config.ts");
  const origins = getFrontendAllowedOrigins();

  assert.ok(origins.includes("http://localhost:3000"));
  assert.ok(origins.includes("http://127.0.0.1:3000"));
  assert.ok(origins.some((origin) => origin.startsWith("http://") && origin.includes(":3000")));
});
