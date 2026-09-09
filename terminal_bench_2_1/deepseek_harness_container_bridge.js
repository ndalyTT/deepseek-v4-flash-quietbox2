"use strict";

const net = require("node:net");

const socketPath = process.env.DSH_RELAY_SOCKET || "/opt/deepseek-relay-runtime/vllm_relay.sock";
const port = Number.parseInt(process.env.DSH_RELAY_PORT || "8011", 10);

const server = net.createServer((client) => {
  const upstream = net.createConnection({ path: socketPath });
  client.pipe(upstream);
  upstream.pipe(client);
  const close = () => {
    client.destroy();
    upstream.destroy();
  };
  client.on("error", close);
  upstream.on("error", close);
});

server.on("error", (error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`DSH_RELAY_BRIDGE_READY port=${port} socket=${socketPath}\n`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
