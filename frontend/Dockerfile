# ---------- Stage 1: build ----------
FROM node:20-alpine AS build
WORKDIR /app

# Install deps with a deterministic lockfile.
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund --prefer-offline

# Copy sources after deps so dep changes don't bust the source layer.
COPY . .

# Vite reads VITE_* at build time only.
ARG VITE_API_BASE_URL=/api
ARG VITE_APP_VERSION=0.1.0
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_VERSION=${VITE_APP_VERSION}

RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine AS runtime

# Drop the default config and ship our SPA-aware one.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static build from stage 1.
COPY --from=build /app/dist /usr/share/nginx/html

# Run as non-root.
RUN addgroup -S spa && adduser -S spa -G spa \
 && chown -R spa:spa /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx \
 && touch /var/run/nginx.pid \
 && chown -R spa:spa /var/run/nginx.pid

USER spa
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
