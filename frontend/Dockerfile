# Frontend do Portal FEJEPE — build Vite servido por nginx.

# ── Build ────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# O Vite congela estas variáveis no bundle em build time. Depois da entrada
# do env-config.js (docker-entrypoint.sh), elas são só o DEFAULT da imagem:
# o que o container receber em runtime tem precedência. Ver src/config/env.ts.
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_USE_MOCK=false
ARG VITE_FEEDBACK_FORM_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_USE_MOCK=${VITE_USE_MOCK} \
    VITE_FEEDBACK_FORM_URL=${VITE_FEEDBACK_FORM_URL}

RUN npm run build

# ── Runtime ──────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Escreve /usr/share/nginx/html/env-config.js no start, a partir das variáveis
# de ambiente do container, e só então executa o CMD.
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1/healthz || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
