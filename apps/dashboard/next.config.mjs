/** @type {import('next').NextConfig} */
const API_URL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
// STATIC_EXPORT=1 → dashboard oddiy HTML/JS fayllarga yig'iladi (out/), Node server kerak emas;
// /api va /media ni nginx API'ga uzatadi (infra/basic/nginx.conf).
const STATIC = process.env.STATIC_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(STATIC
    ? { output: "export", trailingSlash: true }
    : {
        // Dashboard API'ga o'z domeni orqali murojaat qiladi → refresh cookie first-party, CORS muammosi yo'q
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${API_URL}/:path*` },
            { source: "/media/:path*", destination: `${API_URL}/media/:path*` },
          ];
        },
        async headers() {
          return [{
            source: "/:path*",
            headers: [
              { key: "X-Frame-Options", value: "DENY" },
              { key: "X-Content-Type-Options", value: "nosniff" },
              { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
            ],
          }];
        },
      }),
};

export default nextConfig;
