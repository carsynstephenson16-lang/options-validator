#!/usr/bin/env node

// Guard the official Playwright MCP server at the protocol boundary. The
// upstream server's core tool set includes browser_evaluate and
// browser_run_code_unsafe; this project must never advertise or forward them.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const blockedTools = new Set(["browser_evaluate", "browser_run_code_unsafe"]);
const upstream = spawn(
  "npx",
  ["-y", "@playwright/mcp@latest", ...process.argv.slice(2)],
  { cwd: projectRoot, stdio: ["pipe", "pipe", "inherit"] },
);

function keyForId(id) {
  return JSON.stringify(id);
}

function frame(message) {
  return `${JSON.stringify(message)}\n`;
}

function consumeMessages(state, chunk, callback) {
  state.buffer = Buffer.concat([state.buffer, chunk]);
  while (true) {
    const newline = state.buffer.indexOf("\n");
    if (newline < 0) return;
    const line = state.buffer.subarray(0, newline).toString("utf8").replace(/\r$/, "");
    state.buffer = state.buffer.subarray(newline + 1);
    if (line.trim()) callback(JSON.parse(line));
  }
}

const parentState = { buffer: Buffer.alloc(0) };
const upstreamState = { buffer: Buffer.alloc(0) };
const toolListRequests = new Set();

process.stdin.on("data", (chunk) => {
  consumeMessages(parentState, chunk, (message) => {
    if (message.method === "tools/call" && blockedTools.has(message.params?.name)) {
      process.stdout.write(frame({
        jsonrpc: "2.0",
        id: message.id,
        error: { code: -32601, message: `${message.params.name} is disabled by project policy` },
      }));
      return;
    }
    if (message.method === "tools/list" && message.id !== undefined) {
      toolListRequests.add(keyForId(message.id));
    }
upstream.stdin.write(frame(message));
  });
});

upstream.stdout.on("data", (chunk) => {
  consumeMessages(upstreamState, chunk, (message) => {
    const idKey = message.id === undefined ? null : keyForId(message.id);
    if (idKey && toolListRequests.delete(idKey) && Array.isArray(message.result?.tools)) {
      message.result.tools = message.result.tools.filter(
        (tool) => !blockedTools.has(tool?.name),
      );
    }
    process.stdout.write(frame(message));
  });
});

upstream.on("error", (error) => {
  process.stderr.write(`Playwright MCP proxy failed: ${error.name}\n`);
  process.exitCode = 1;
});

upstream.on("close", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exitCode = code ?? 1;
});
