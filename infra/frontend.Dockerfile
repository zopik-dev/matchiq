# MatchIQ frontend — multi-stage: Node builds the static bundle, nginx serves it
# and reverse-proxies /api/* to the backend container (same origin for the app).
FROM node:20-alpine AS build

WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Bake the API base URL at build time (defaults to the compose backend).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY infra/nginx.docker.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
