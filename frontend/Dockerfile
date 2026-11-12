# 小码前端镜像（多阶段构建，Next.js standalone 输出）
FROM node:26-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# 使用 BuildKit 缓存加速重复构建；跳过 audit/fund 网络请求
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM node:26-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:26-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
