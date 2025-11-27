FROM node:18-alpine as builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
# Copy SSL certs
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY landing.html /usr/share/nginx/html/index.html
COPY --from=builder /app/dist/bizdnaii-widget.js /usr/share/nginx/html/bizdnaii-widget.js
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
