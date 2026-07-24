const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

autoUpdater.checkForUpdatesAndNotify();
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'lafm',
  repo: 'crypto-trading-app',
});

autoUpdater.on('update-available', () => {
  console.log('Update available. Downloading...');
});

autoUpdater.on('update-downloaded', () => {
  console.log('Update downloaded. Will install on restart.');
  mainWindow?.webContents.send('update-downloaded');
});

let mainWindow = null;
let backendProcess = null;

function getBackendExecutable() {
  if (app.isPackaged) {
    const resourcesExe = path.join(process.resourcesPath, 'trading_app.exe');
    if (fs.existsSync(resourcesExe)) {
      return resourcesExe;
    }
    const asarExe = path.join(__dirname, '..', 'backend', 'trading_app.exe');
    if (fs.existsSync(asarExe)) {
      return asarExe;
    }
  }
  return path.join(__dirname, '..', 'backend', 'main.py');
}

function getBackendCommand() {
  const exe = getBackendExecutable();
  if (exe.endsWith('.exe')) {
    return { command: exe, args: [] };
  }
  return { command: 'python', args: [exe] };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: 'Crypto Trading Terminal - LAFM',
    backgroundColor: '#0f172a',
  });

  const iconPath = path.join(__dirname, '..', 'assets', 'icon.png');
  if (fs.existsSync(iconPath)) {
    mainWindow.setIcon(iconPath);
  }

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    stopBackend();
    mainWindow = null;
  });
}

function startBackend() {
  const { command, args } = getBackendCommand();
  const cwd = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..', 'backend');

  console.log(`Starting backend: ${command} ${args.join(' ')} in ${cwd}`);

  backendProcess = spawn(command, args, {
    cwd,
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err);
  });

  backendProcess.on('exit', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    try {
      backendProcess.kill('SIGTERM');
      const timeout = setTimeout(() => {
        if (backendProcess) {
          backendProcess.kill('SIGKILL');
        }
      }, 5000);
      backendProcess.on('exit', () => clearTimeout(timeout));
    } catch (e) {
      console.error('Error stopping backend:', e);
    }
    backendProcess = null;
  }
}

app.whenReady().then(() => {
  createWindow();
  setTimeout(startBackend, 500);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('select-license-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [{ name: 'License Files', extensions: ['lic', 'key', 'txt'] }],
  });
  return result.canceled ? null : result.filePaths[0];
});

