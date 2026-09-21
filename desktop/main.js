const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

const BACKEND_URL = "http://127.0.0.1:8420";
const HEALTH_URL = `${BACKEND_URL}/api/health`;
const BACKEND_DIR_NAME = "rabbit-hole-backend";
const BACKEND_EXE_NAME = process.platform === "win32" ? "rabbit-hole-backend.exe" : "rabbit-hole-backend";

let backendProcess = null;
let mainWindow = null;

/** In dev (npm start, unpacked) the bundle lives next to this file, built by
 * desktop/build_backend.py into backend/dist/. Packaged by electron-builder,
 * it ships under process.resourcesPath instead (see package.json's
 * extraResources) — asar-unpacked since it's a native binary, not JS. */
function backendPath() {
  const base = app.isPackaged
    ? path.join(process.resourcesPath, BACKEND_DIR_NAME)
    : path.join(__dirname, "..", "backend", "dist", BACKEND_DIR_NAME);
  return path.join(base, BACKEND_EXE_NAME);
}

function waitForHealth(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    function attempt() {
      const req = http.get(HEALTH_URL, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      req.on("error", retry);
      req.setTimeout(2000, () => req.destroy());
    }
    function retry() {
      if (Date.now() > deadline) return reject(new Error("Backend did not become healthy in time"));
      setTimeout(attempt, 500);
    }
    attempt();
  });
}

function startBackend() {
  const exe = backendPath();
  backendProcess = spawn(exe, [], { stdio: "pipe" });
  backendProcess.stdout.on("data", (d) => process.stdout.write(`[backend] ${d}`));
  backendProcess.stderr.on("data", (d) => process.stderr.write(`[backend] ${d}`));
  backendProcess.on("error", (err) => {
    dialog.showErrorBox("Rabbit Hole", `Couldn't start the backend:\n${err.message}`);
    app.quit();
  });
  backendProcess.on("exit", (code) => {
    if (code !== 0 && code !== null) {
      dialog.showErrorBox("Rabbit Hole", `The backend exited unexpectedly (code ${code}). Check logs and restart the app.`);
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "Rabbit Hole",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  mainWindow.loadURL(BACKEND_URL);
}

app.whenReady().then(async () => {
  startBackend();
  try {
    await waitForHealth(30000);
  } catch (err) {
    dialog.showErrorBox("Rabbit Hole", `The app took too long to start:\n${err.message}`);
    app.quit();
    return;
  }
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});
