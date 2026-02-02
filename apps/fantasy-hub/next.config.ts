import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  basePath: process.env.NODE_ENV === "production" ? "/fantasy" : "",
  assetPrefix: process.env.NODE_ENV === "production" ? "/fantasy/" : "",
  trailingSlash: true,
};

export default nextConfig;
