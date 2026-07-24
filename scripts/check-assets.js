const fs = require('fs');
const path = require('path');

const iconPath = path.join(__dirname, '..', 'assets', 'icon.png');

if (!fs.existsSync(iconPath)) {
  console.warn('[WARN] assets/icon.png is missing. Electron will use the default icon.');
  console.warn('[WARN] For production builds, add a 512x512 PNG to assets/icon.png.');
}
