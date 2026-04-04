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

    // Build PYTHONPATH to include the Python source directory
    const pythonSrcPath = path.join(this.config.spawn.cwd, "src");
    const pythonPathEnv = this.joinPathEnv(pythonSrcPath, process.env.PYTHONPATH);

    // Determine the Python command - try multiple options on Windows
    let pythonCmd = this.config.spawn.command;
    
    // On Windows, prefer using 'py' launcher which handles Python versions better
    if (process.platform === "win32") {
      const originalCmd = pythonCmd;
      // If using plain 'python', switch to 'py'
      if (pythonCmd === "python" || pythonCmd === "python.exe") {
        pythonCmd = "py";
        this.logger.info(`Detected Windows, using 'py' launcher instead of '${originalCmd}'`);
      } else if (pythonCmd === "py") {
        this.logger.info(`Using Windows 'py' launcher`);
      }
      
      // Validate the working directory is correct - it should point to the python source
      const expectedPath = path.join(this.config.spawn.cwd, "src", "gnosys_backend");
      this.logger.info(`Expected backend path: ${expectedPath}`);
      
      // Log the actual user config if cwd looks wrong
      if (!this.config.spawn.cwd.includes("Desktop") && !this.config.spawn.cwd.includes("Gnosys")) {
        this.logger.warn(`Working directory '${this.config.spawn.cwd}' may be incorrect.`);
        this.logger.warn(`Expected path containing 'Desktop' and 'Gnosys'.`);
        this.logger.warn(`Update spawn.cwd in your OpenClaw config to point to the correct directory.`);
      }
    }

    this.logger.info(`Starting Gnosys backend: ${pythonCmd} ${this.config.spawn.args.join(" ")}`);
    this.logger.info(`Working directory: ${this.config.spawn.cwd}`);
    this.logger.info(`PYTHONPATH: ${pythonPathEnv}`);
    this.logger.info(`Backend URL: ${this.config.backendUrl}`);

    const env = {
      ...process.env,
      PYTHONPATH: pythonPathEnv,
      GNOSYS_HOST: this.config.spawn.host,
      GNOSYS_PORT: String(this.config.spawn.port),
      GNOSYS_DB_PATH: this.config.spawn.dbPath,
      GNOSYS_VECTORS_PATH: this.config.spawn.vectorsPath,
      GNOSYS_RETENTION_EPISODIC_DAYS: String(this.config.retention.episodicDays),
      GNOSYS_RETENTION_ARCHIVE_DAYS: String(this.config.retention.archiveDays),
      GNOSYS_DEFAULT_SEARCH_LIMIT: String(this.config.retention.defaultSearchLimit),
      GNOSYS_EMBEDDINGS_PROVIDER: this.config.embeddings.provider,
      ...this.config.spawn.env
    };

    const child = spawn(pythonCmd, this.config.spawn.args, {
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
      
      // Provide specific guidance for common Windows issues
      if (error.code === "ENOENT") {
        const cmd = pythonCmd;
        this.logger.error(`The command '${cmd}' was not found.`);
        this.logger.error(`On Windows, try using 'py' instead of 'python':`);
        this.logger.error(`  "spawn": { "command": "py", "args": ["-m", "gnosys_backend.app"] }`);
        this.logger.error(`Or ensure Python is in your PATH by running: where python`);
      }
      
      this.logger.error(`Please verify:`);
      this.logger.error(`  1. Python is installed: py --version (Windows) / python3 --version (Linux/Mac)`);
      this.logger.error(`  2. Working directory exists: ${this.config.spawn.cwd}`);
      this.logger.error(`  3. Python source path exists: ${pythonSrcPath}`);
      this.logger.error(`  4. Dependencies are installed: pip install -e ./python`);
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
    let attempts = 0;
    while (Date.now() < deadline) {
      attempts++;
      try {
        await this.client.health();
        this.logger.info(`Gnosys backend health check passed after ${attempts} attempt(s)`);
        return;
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        if (attempts <= 3) {
          this.logger.info(`Health check attempt ${attempts} failed: ${errorMsg}`);
        }
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    throw new Error(`Timed out starting spawned Gnosys backend at ${this.config.backendUrl} after ${attempts} attempts. Check that port ${this.config.spawn.port} is available and the backend can start successfully.`);
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
