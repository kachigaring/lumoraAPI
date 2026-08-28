// Tiny file-based data store. No database needed for a starter tool.
import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export const DATA_DIR = join(__dirname, '..', 'data');
export const UPLOAD_DIR = join(DATA_DIR, 'uploads');

/** Make sure the data folders and starting files exist. */
export function ensureData() {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });
  if (!existsSync(UPLOAD_DIR)) mkdirSync(UPLOAD_DIR, { recursive: true });
  seed('jobs.json', 'jobs.sample.json');
  seed('candidates.json', null);
}

function seed(realName, sampleName) {
  const real = join(DATA_DIR, realName);
  if (existsSync(real)) return;
  const sample = sampleName ? join(DATA_DIR, sampleName) : null;
  if (sample && existsSync(sample)) copyFileSync(sample, real);
  else writeFileSync(real, '[]');
}

export function read(name) {
  const p = join(DATA_DIR, name);
  if (!existsSync(p)) return [];
  try {
    return JSON.parse(readFileSync(p, 'utf8'));
  } catch {
    return [];
  }
}

export function write(name, data) {
  writeFileSync(join(DATA_DIR, name), JSON.stringify(data, null, 2));
}
