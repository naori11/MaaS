# 1. Use the dedicated image based on stack currently used
# As much as possible, use the slim version of the image to reduce the attack surface and the size of the image.
# Base image: Official lightweight NGINX Alpine image
FROM nginx:alpine

# 2. Remove the default NGINX configuration file from the image installation
RUN rm -f /etc/nginx/conf.d/default.conf

# 3. Copy custom NGINX configuration into standard configuration path
COPY nginx.conf /etc/nginx/nginx.conf

# 4. Create self-signed SSL/TLS certificates into the container
# Since there is no dedicated domain as of now, certificates would be self-signed or generated locally within the image.
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/localhost-key.pem \
    -out /etc/nginx/certs/localhost.pem \
    -subj "/C=US/ST=Dev/L=Local/O=MaaS/CN=localhost"

# 5. Expose standard HTTP and HTTPS ports within the container
EXPOSE 80 443

# 6. Run NGINX in foreground to keep container active
# daemon off ensures NGINX runs in the foreground and keeps the container active.
CMD ["nginx", "-g", "daemon off;"]
