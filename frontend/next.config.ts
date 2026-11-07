import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 部署使用 standalone 输出
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;
