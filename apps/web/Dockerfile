FROM node:22-slim AS dependencies
WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json apps/web/package.json
COPY lib lib
COPY artifacts artifacts
COPY scripts scripts
RUN pnpm install --filter @parken/web --frozen-lockfile

FROM dependencies AS builder
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=${NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN}
ENV NEXT_TELEMETRY_DISABLED=1 DOCKER_BUILD=1
RUN pnpm --filter @parken/web build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /workspace/apps/web/.next/standalone ./
COPY --from=builder /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /workspace/apps/web/public ./apps/web/public
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
