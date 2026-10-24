import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // El móvil y los portátiles del equipo abren la web por IP, por nombre .local (Bonjour) o por túnel;
  // sin esto `next dev` bloquea sus recursos y la página no llega a arrancar.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*", "*.local", "*.trycloudflare.com"],
  // Un único puerto (:3000) para PC y móvil: /api/* se reenvía al backend FastAPI, sin CORS.
  async rewrites() {
    const backendUrl = process.env.FASTAPI_INTERNAL_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
