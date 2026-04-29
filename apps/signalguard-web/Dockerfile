# syntax=docker/dockerfile:1.7
# cstack signalguard-web: Next.js 15 dashboard. Standalone output gated
# behind BUILD_STANDALONE=true (see next.config.ts) so a Linux container
# build produces the self-contained server bundle while Windows local
# pnpm builds keep the default-off behaviour that avoids EPERM symlink
# failures.

FROM node:22-bookworm-slim AS builder

ENV PNPM_HOME="/pnpm" \
    PATH="$PNPM_HOME:$PATH" \
    BUILD_STANDALONE=true

RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /repo

# Workspace metadata + tooling configs separately so dependency install
# is cached when only source files change.
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json .npmrc ./
COPY tsconfig.base.json eslint.config.mjs .prettierrc.json .prettierignore commitlint.config.mjs ./

# The web app reads the OpenAPI spec from the api app at build time to
# regenerate the typed client; copy the spec ahead of the source.
COPY apps/signalguard-api/openapi.json ./apps/signalguard-api/openapi.json

COPY apps/signalguard-web/ ./apps/signalguard-web/

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter signalguard-web

RUN pnpm --filter signalguard-web run build


FROM node:22-bookworm-slim AS runtime

RUN groupadd --system --gid 1001 cstack && \
    useradd --system --uid 1001 --gid cstack --create-home cstack

WORKDIR /app

# Standalone output ships its own minimal node_modules and a server.js
# entry; copy the standalone tree and the built static assets. The
# signalguard-web app has no public/ directory (no favicon or static
# files outside of .next/static); add it back to this Dockerfile
# only when one is introduced.
COPY --from=builder --chown=cstack:cstack /repo/apps/signalguard-web/.next/standalone ./
COPY --from=builder --chown=cstack:cstack /repo/apps/signalguard-web/.next/static \
        ./apps/signalguard-web/.next/static

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_PUBLIC_API_BASE_URL=http://api:8000

USER cstack

EXPOSE 3000

CMD ["node", "apps/signalguard-web/server.js"]
