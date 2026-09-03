# Stage 1: build the frontend as static files
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# Empty by default so the built JS calls same-origin relative paths
# (/api/..., /uploads/...) instead of a baked-in host — Nginx below proxies
# those to the backend, so no CORS setup is needed in production.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Stage 2: serve the build output and reverse-proxy API/upload requests
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
