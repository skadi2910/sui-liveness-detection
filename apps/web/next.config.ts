import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@sui-human/shared"],
  output: "standalone",
  turbopack: {
    resolveAlias: {
      "@tensorflow-models/face-detection": "./shims/tfjs-face-detection.ts",
    },
  },
};

export default nextConfig;
