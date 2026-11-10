export function getGatewayBaseUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "").trim().replace(/\/$/, "");
  if (typeof window !== "undefined") {
    // If running in browser and configured URL points to localhost but the page is served
    // from a non-localhost host (like ngrok or a remote cloud domain), fallback to relative ""
    // so requests flow same-origin through the edge reverse proxy.
    if (configured && configured.includes("localhost") && !window.location.hostname.includes("localhost")) {
      return "";
    }
  }
  return configured;
}
