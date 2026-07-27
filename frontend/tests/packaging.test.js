import { describe, it, expect } from 'vitest';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

describe('Packaging prerequisites', () => {
  const rootDir = join(__dirname, '..', '..');

  it('should have assets/icon.png present', () => {
    const fs = require('fs');
    const path = require('path');
    const iconPath = path.join(rootDir, 'assets', 'icon.png');
    expect(fs.existsSync(iconPath)).toBe(true);
  });

  it('should have icon.png with minimum required size', () => {
    const fs = require('fs');
    const path = require('path');
    const iconPath = path.join(rootDir, 'assets', 'icon.png');
    const stat = fs.statSync(iconPath);
    expect(stat.size).toBeGreaterThan(0);
  });
});
