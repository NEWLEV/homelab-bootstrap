FROM node:22-slim

WORKDIR /work
COPY server.js /usr/local/bin/openclaw-server.js
COPY start.sh /usr/local/bin/openclaw-start
COPY healthcheck.sh /usr/local/bin/openclaw-healthcheck
COPY ui /usr/local/share/openclaw-ui
RUN chmod 755 /usr/local/bin/openclaw-server.js /usr/local/bin/openclaw-start /usr/local/bin/openclaw-healthcheck

ENV OPENCLAW_UI_DIR=/usr/local/share/openclaw-ui

ENTRYPOINT ["/usr/local/bin/openclaw-start"]
