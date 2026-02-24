import pino from "pino";
import fs from "fs";
import path from "path";

const logsDir = path.join(process.cwd(), "logs");
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

const level = process.env.NODE_ENV === "production" ? "info" : "debug";

const streams: pino.StreamEntry[] = [
  // Stdout — human-readable in dev
  {
    level,
    stream: process.stdout,
  },
  // File — JSON lines for persistent storage
  {
    level,
    stream: pino.destination(path.join(logsDir, "discovery.log")),
  },
];

const logger = pino(
  {
    level,
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      bindings: (bindings) => ({ pid: bindings.pid, host: bindings.hostname }),
    },
  },
  pino.multistream(streams)
);

export default logger;
