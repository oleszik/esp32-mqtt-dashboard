FROM eclipse-mosquitto:2.0.21

COPY config/mosquitto.conf /mosquitto/config/mosquitto.conf
COPY config/acl /mosquitto/config/acl
COPY docker-entrypoint-local.sh /usr/local/bin/docker-entrypoint-local.sh

USER root
RUN apk add --no-cache su-exec \
    && chmod 755 /usr/local/bin/docker-entrypoint-local.sh \
    && mkdir -p /mosquitto/runtime /mosquitto/data \
    && chown -R mosquitto:mosquitto /mosquitto/runtime /mosquitto/data \
    && chown mosquitto:mosquitto /mosquitto/config/mosquitto.conf /mosquitto/config/acl \
    && chmod 600 /mosquitto/config/mosquitto.conf \
    && chmod 700 /mosquitto/config/acl
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-local.sh"]
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]

