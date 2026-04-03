import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import path from "node:path";

import type { PluginLogger } from "openclaw/plugin-sdk/plugin-entry";

import type { NormalizedGnosysPluginConfig } from "../config.js";
import { GnosysBackendClient } from "./client.js";

type ProcessState = "idle" | "starting" | "running" | "failed" | "stopped";

export class GnosysBackendProcessManager {
  private child: ChildProcessWithoutNullStreams | null = null;
  private startPromise: Promise<void> | null = null;
  private state: ProcessState = "idle";
  private recentOutput: string[] = [];
  private lastError: string | null = null;

  constructor(
    private readonly config: NormalizedGnosysPluginConfig,
    private readonly client: GnosysBackendClient,
    private readonly logger: PluginLogger
  ) {}

  getDiagnostics(): { state: ProcessState; pid?: number; recentOutput: string[]; lastError?: string } {
    return {
      state: this.state,
      pid: this.child?.pid,
      recentOutput: [...this.recentOutput],
      lastError: this.lastError ?? undefined
    };
  }

  async ensureStarted(): Promise<void> {
    if (this.config.mode !== "spawn-local-python-backend") {
      return;
    }
    if (this.child && !this.child.killed) {
      return;
    }
    this.startPromise ??= this.startInternal();
    await this.startPromise;
  }

  async stop(): Promise<void> {
    const child = this.child;
    this.child = null;
    this.startPromise = null;
    if (!child || child.killed) {
      this.state = "stopped";
      return;
    }
    await new Promise<void>((resolve) => {
      child.once("exit", () => resolve());
      child.kill();
      setTimeout(() => resolve(), 2_000);
    });
    this.state = "stopped";
  }

  private async startInternal(): Promise<void> {
    this.state = "starting";
    this.lastError = null;

    const env = {
      ...process.env,
      PYTHONPATH: this.joinPathEnv(path.join(this.config.spawn.cwd, "src"), process.env.PYTHONPATH),
      GNOSYS_HOST: this.config.spawn.host,
      GNOSYS_PORT: String(this.config.spawn.port),
      GNOSYS_DB_PATH: this.config.spawn.dbPath,
      GNOSYS_RETENTION_EPISODIC_DAYS: String(this.config.retention.episodicDays),
      GNOSYS_RETENTION_ARCHIVE_DAYS: String(this.config.retention.archiveDays),
      GNOSYS_DEFAULT_SEARCH_LIMIT: String(this.config.retention.defaultSearchLimit),
      ...this.config.spawn.env
    };

    const child = spawn(this.config.spawn.command, this.config.spawn.args, {
      cwd: this.config.spawn.cwd,
      env,
      stdio: "pipe"
    });

    this.child = child;
    child.stdout.on("data", (chunk) => this.captureOutput(String(chunk)));
    child.stderr.on("data", (chunk) => this.captureOutput(String(chunk)));
    child.once("exit", (code, signal) => {
      if (this.state === "running") {
        this.state = "failed";
        this.lastError = `Spawned Gnosys backend exited unexpectedly (code=${code ?? "null"}, signal=${signal ?? "null"})`;
        this.logger.warn(this.lastError);
      }
      this.child = null;
      this.startPromise = null;
    });
    child.once("error", (error) => {
      this.state = "failed";
      this.lastError = error.message;
      this.logger.error(`Failed to spawn Gnosys backend: ${error.message}`);
    });

    try {
      await this.waitForHealth();
      this.state = "running";
      this.logger.info(`Gnosys backend ready at ${this.config.backendUrl}`);
    } catch (error) {
      this.state = "failed";
      this.lastError = error instanceof Error ? error.message : String(error);
      await this.stop();
      throw error;
    } finally {
      this.startPromise = null;
    }
  }

  private async waitForHealth(): Promise<void> {
    const deadline = Date.now() + this.config.spawn.startupTimeoutMs;
    while (Date.now() < deadline) {
      try {
        await this.client.health();
        return;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    throw new Error(`Timed out starting spawned Gnosys backend at ${this.config.backendUrl}`);
  }

  private captureOutput(text: string): void {
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }
      this.recentOutput.push(trimmed);
      if (this.recentOutput.length > 20) {
        this.recentOutput.shift();
      }
    }
  }

  private joinPathEnv(value: string, current: string | undefined): string {
    return current ? `${value}${path.delimiter}${current}` : value;
  }
}
