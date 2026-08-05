#!/usr/bin/env node
const http = require('node:http');

const config = {
  configDir: process.env.OPENCLAW_CONFIG_DIR || '/config',
  stateDir: process.env.OPENCLAW_STATE_DIR || '/state',
  secretsFile: process.env.OPENCLAW_SECRETS_FILE || '/run/secrets/openclaw_env',
  localRagUrl: process.env.OPENCLAW_LOCAL_RAG_URL || 'http://local-rag-api:8080',
  gatewayBind: process.env.OPENCLAW_GATEWAY_BIND || '127.0.0.1',
  gatewayPort: Number.parseInt(process.env.OPENCLAW_GATEWAY_PORT || '18789', 10),
  nodeCompileCache: process.env.NODE_COMPILE_CACHE || '/var/tmp/openclaw-compile-cache',
  noRespawn: process.env.OPENCLAW_NO_RESPAWN || '1',
};

const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    const body = JSON.stringify({
      status: 'ok',
      gatewayBind: config.gatewayBind,
      gatewayPort: config.gatewayPort,
      localRagUrl: config.localRagUrl,
      secretsFile: config.secretsFile,
      stateDir: config.stateDir,
      configDir: config.configDir,
    });

    res.writeHead(200, {
      'content-type': 'application/json; charset=utf-8',
      'content-length': Buffer.byteLength(body),
    });
    res.end(body);
    return;
  }

  if (req.url === '/' || req.url === '/ready') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('openclaw ready
');
    return;
  }

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('not found
');
});

server.listen(config.gatewayPort, config.gatewayBind, () => {
  process.stdout.write(
    `OpenClaw runtime ready on ${config.gatewayBind}:${config.gatewayPort}
`,
  );
});

process.on('SIGTERM', () => server.close(() => process.exit(0)));
process.on('SIGINT', () => server.close(() => process.exit(0)));
