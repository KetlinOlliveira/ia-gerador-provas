# syntax=docker/dockerfile:1

# ---------- desenvolvimento: servidor do Vite com o código montado via volume ----------
FROM node:24-alpine AS desenvolvimento
WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---------- build: arquivos estáticos ----------
FROM desenvolvimento AS build
COPY . .
RUN npm run build

# ---------- producao: nginx servindo o build e repassando /api ao backend ----------
FROM nginx:1.27-alpine AS producao
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
