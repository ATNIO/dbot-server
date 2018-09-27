FROM tiangolo/uwsgi-nginx:python3.6

COPY dbot-server/requirements.txt /requirements.txt
# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /requirements.txt

# By default, allow unlimited file sizes, modify it to limit the file sizes
# To have a maximum of 1 MB (Nginx's default) change the line to:
# ENV NGINX_MAX_UPLOAD 1m
ENV NGINX_MAX_UPLOAD 0

# By default, dbot-server run as production
ENV APP_ENV Production

# By default, dbot-server connects with local atnchain node
ENV WEB3_PROVIDER http://0.0.0.0:4545

# By default, Nginx listens on port 80.
# To modify this, change LISTEN_PORT environment variable.
# (in a Dockerfile or with an option for `docker run`)
ENV LISTEN_PORT 80

# Which uWSGI .ini file should be used, to make it customizable
ENV UWSGI_INI /dbot-server/uwsgi.ini

# URL under which static (not modified by Python) files will be requested
# They will be served by Nginx directly, without being handled by uWSGI
ENV STATIC_URL /static
# Absolute path in where the static files wil be
ENV STATIC_PATH /dbot-server/static

# If STATIC_INDEX is 1, serve / with /static/index.html directly (or the static URL configured)
ENV STATIC_INDEX 0

# Add app
COPY dbot-server /dbot-server
WORKDIR /dbot-server
# Make /dbot-server/* available to be imported by Python globally to better support several use cases like Alembic migrations.
ENV PYTHONPATH=/dbot-server

# start.sh script will check for a /app/prestart.sh script and run it before starting the app (e.g. for migrations)
# And then will start Supervisor, which in turn will start Nginx and uWSGI
RUN chmod +x /dbot-server/start.sh

# entrypoint.sh will generate Nginx additional configs
RUN chmod +x /dbot-server/entrypoint.sh

ENTRYPOINT ["/dbot-server/entrypoint.sh"]

# Run the start script
CMD ["/dbot-server/start.sh"]
