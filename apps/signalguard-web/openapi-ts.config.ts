import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: '../signalguard-api/openapi.json',
  output: {
    path: 'src/lib/api/generated',
    format: 'prettier',
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/schemas',
    '@hey-api/typescript',
    '@hey-api/sdk',
    {
      name: '@tanstack/react-query',
      // Pagination is URL-driven (offset/limit query params); the dashboard
      // does not need infinite-scroll helpers, and the generated infinite
      // helpers fight TypeScript's inference on wrapper-shaped responses.
      // Mutations are wrapped by hand so we can scope optimistic updates;
      // the auto-generated mutation helpers also confuse the compiler.
      infiniteQueryOptions: false,
      mutationOptions: false,
    },
  ],
});
