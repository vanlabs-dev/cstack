import type { NextConfig } from 'next';

// `output: 'standalone'` produces the self-contained server bundle the
// Docker runtime stage copies into the slim image. The Dockerfile passes
// BUILD_STANDALONE=true at build time. Local Windows pnpm builds cannot
// produce the standalone output because the trace step symlinks
// node_modules entries and EPERMs without SeCreateSymbolicLinkPrivilege;
// leaving standalone off by default keeps `pnpm build` working on a
// Windows dev machine.
const standalone = process.env.BUILD_STANDALONE === 'true';

const config: NextConfig = {
  output: standalone ? 'standalone' : undefined,
  experimental: {
    typedRoutes: true,
  },
};

export default config;
