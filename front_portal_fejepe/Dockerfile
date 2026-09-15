# Frontend do Portal FEJEPE — build Vite servido por nginx.

# ── Build ────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# O Vite congela estas variáveis no bundle em build time.
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_USE_MOCK=false
ARG VITE_FEEDBACK_FORM_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY} \
    VITE_USE_MOCK=${VITE_USE_MOCK} \
    VITE_FEEDBACK_FORM_URL=${VITE_FEEDBACK_FORM_URL}

RUN npm run build

# ── Runtime ──────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
