import type { NextConfig } from "next";

// Fully static site: `next build` writes plain HTML/JS to out/. The pipeline puts
// its JSON and newsletter HTML in public/, so there is no server or API at runtime.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
