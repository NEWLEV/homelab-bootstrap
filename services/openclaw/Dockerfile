FROM node:22-slim

WORKDIR /work
COPY start.sh /usr/local/bin/openclaw-start
RUN chmod 755 /usr/local/bin/openclaw-start

ENTRYPOINT ["/usr/local/bin/openclaw-start"]
