FROM eclipse-mosquitto:2.0.21

COPY config/mosquitto.conf /mosquitto/config/mosquitto.conf
COPY config/acl /mosquitto/config/acl
COPY docker-entrypoint-local.sh /usr/local/bin/docker-entrypoint-local.sh

USER root
RUN chmod 755 /usr/local/bin/docker-entrypoint-local.sh \
    && mkdir -p /mosquitto/runtime /mosquitto/data \
    && chown -R mosquitto:mosquitto /mosquitto/runtime /mosquitto/data
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-local.sh"]
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]

