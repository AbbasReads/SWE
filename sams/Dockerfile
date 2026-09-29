# App container: Apache + mod_wsgi serving the Flask app (Linux / Apache per the problem statement)
FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends apache2 libapache2-mod-wsgi-py3 python3-flask python3-pymysql \
 && rm -rf /var/lib/apt/lists/*

COPY app.py db.py models.py schema.sql sams.wsgi /srv/sams/
COPY templates /srv/sams/templates
COPY static /srv/sams/static
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]
