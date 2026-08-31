FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*

COPY code/web_application/index.html /usr/share/nginx/html/index.html
COPY code/web_application/script.js /usr/share/nginx/html/script.js

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]