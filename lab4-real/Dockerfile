# FIRST CONTAINER
# Installing python dependencies
FROM python:3 AS base

WORKDIR /usr/src/app

RUN ["apt", "install", "git"]
RUN git clone https://github.com/purduecyan/docsy

WORKDIR ./docsy
RUN ["python3", "-m", "venv", ".venv"]
RUN pip install \
    sphinx \
    sphinx-rtd-theme \
    sphinx-copybutton \
    sphinx-prompt \
    myst-parser \
    sphinx-autobuild \
    sphinx-design \
    sphinxcontrib-mermaid \
    sphinxcontrib-httpdomain \
    sphinxcontrib-serializinghtml \
    sphinx-intl \
    sphinx-git
RUN /bin/bash -c "source .venv/bin/activate && pip install ."

# Building the documentation
WORKDIR ./docs
RUN ["make", "html"]

# SECOND CONTAINER
# Serving the docsy pages
FROM nginx:latest AS serve

# Copy the built HTML documentation from the build stage
COPY --from=base /usr/src/app/docsy/docs/build/html /usr/share/nginx/html

# Create necessary nginx cache directories and set proper permissions
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp \
    && chown -R nginx:nginx /var/cache/nginx \
    && chmod -R 755 /var/cache/nginx

# Update nginx configuration to listen on port 8080
RUN sed -i 's/listen       80;/listen       8080;/' /etc/nginx/conf.d/default.conf \
    && sed -i 's/listen  \[::\]:80;/listen  [::]:8080;/' /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]