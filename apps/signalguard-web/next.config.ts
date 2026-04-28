import type { NextConfig } from 'next';

// `output: 'standalone'` is the right deploy target but symlinks the pnpm
// store into .next/standalone, which fails on Windows without
// SeCreateSymbolicLinkPrivilege. The container deploy sprint can re-enable
// it on Linux CI; for local dev/build the default output is enough.
const config: NextConfig = {
  experimental: {
    typedRoutes: true,
  },
};

export default config;
