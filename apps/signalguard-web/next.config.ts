import type { NextConfig } from "next";

const config: NextConfig = {
  experimental: {
    typedRoutes: true,
  },
  output: "standalone",
};

export default config;
