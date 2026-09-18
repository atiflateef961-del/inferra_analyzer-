import { networkInterfaces } from "node:os";

export function getLanIpv4Address(): string | null {
  if (typeof window !== "undefined") {
    return null;
  }

  const interfaces = networkInterfaces();

  for (const values of Object.values(interfaces)) {
    if (!values) continue;
    for (const candidate of values) {
      if (candidate.family === "IPv4" && !candidate.internal && !candidate.address.startsWith("169.254.")) {
        return candidate.address;
      }
    }
  }

  return null;
}

export function getDefaultBackendUrl(): string {
  const configured = process.env.BACKEND_URL?.trim();
  if (configured) {
    return configured;
  }

  const lanIp = getLanIpv4Address();
  if (lanIp) {
    return `http://${lanIp}:8000`;
  }

  return "http://127.0.0.1:8000";
}

export function getFrontendAllowedOrigins(): string[] {
  const origins = ["http://localhost:3000", "http://127.0.0.1:3000"];
  const lanIp = getLanIpv4Address();
  if (lanIp) {
    origins.push(`http://${lanIp}:3000`);
  }
  return [...new Set(origins)];
}
