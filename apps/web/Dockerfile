# -------------------------------------------------------------------------------------------------
# Next.js Production Multi-Stage Dockerfile
#
# Multi-stage builds separate the build environment (Node, pnpm, devDependencies, compilers)
# from the lean production runtime.
# Next.js "standalone" mode produces an ultra-small image (~120MB instead of >1GB)
# containing only the code and dependencies actually used at runtime.
# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------------
# Stage 1: Base image with pnpm enabled
# -------------------------------------------------------------
# Use official Node 20 Alpine for minimal image size and attack surface.
FROM node:20-alpine AS base

# Install libc6-compat (required by Alpine Linux for compatibility with certain Node native bindings)
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Enable Corepack and activate pnpm matching the repository's packageManager version
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate

# -------------------------------------------------------------
# Stage 2: Install dependencies
# -------------------------------------------------------------
FROM base AS deps
WORKDIR /app

# Copy root monorepo files required by pnpm for workspace dependency resolution.
# By copying lockfiles separately, Docker layer caching avoids re-installing
# packages unless the lockfile or package.json changes.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/

# Install dependencies strictly matching the lockfile
RUN pnpm install --frozen-lockfile

# -------------------------------------------------------------
# Stage 3: Build the application
# -------------------------------------------------------------
FROM base AS builder
WORKDIR /app

# Copy workspace configuration and web application source code
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web ./apps/web

# Copy cached dependencies from the deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules

# Disable Next.js telemetry during build to speed up compilation and protect privacy
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Compile Next.js in standalone mode (configured in apps/web/next.config.ts)
RUN pnpm --filter web build

# -------------------------------------------------------------
# Stage 4: Production runner
# -------------------------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Security best practice: Create a dedicated non-root user/group to run the application
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Ensure public assets directory exists
RUN mkdir -p ./apps/web/public
COPY --from=builder /app/apps/web/package.json ./apps/web/package.json

# Copy standalone build output and static assets from builder stage
# Next.js standalone preserves monorepo folder hierarchy (apps/web/server.js)
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static

# Switch from root to unprivileged user
USER nextjs

# Expose Next.js server port
EXPOSE 3000

# Start Next.js standalone server
CMD ["node", "apps/web/server.js"]
