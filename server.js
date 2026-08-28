// Lumora API — job-lead board + CV database.
// Start with:  npm start     (or double-click start.bat)
import 'dotenv/config';
import express from 'express';
import multer from 'multer';
import { extname, join, dirname } from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

import { ensureData, read, write, UPLOAD_DIR } from './src/store.js';
import { refreshJobs, isLive } from './src/jobs.js';
import { SECTORS } from './src/sectors.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const POLL_MINUTES = Number(process.env.POLL_MINUTES || 15);

ensureData();

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(join(__dirname, 'public')));
app.use('/cv', express.static(UPLOAD_DIR)); // download submitted CVs

// ---------- CV upload handling ----------
const ALLOWED = new Set(['.pdf', '.doc', '.docx']);
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  filename: (req, file, cb) =>
    cb(null, `${Date.now()}-${randomUUID().slice(0, 8)}${extname(file.originalname).toLowerCase()}`)
});
const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (req, file, cb) => cb(null, ALLOWED.has(extname(file.originalname).toLowerCase()))
});

// ---------- API ----------
app.get('/api/config', (req, res) => {
  res.json({
    live: isLive(),
    sectors: Object.fromEntries(Object.entries(SECTORS).map(([k, v]) => [k, v.label]))
  });
});

app.get('/api/leads', (req, res) => {
  const { sector, status, q } = req.query;
  let jobs = read('jobs.json');
  if (sector && sector !== 'all') jobs = jobs.filter((j) => j.sector === sector);
  if (status && status !== 'all') jobs = jobs.filter((j) => j.status === status);
  if (q) {
    const s = String(q).toLowerCase();
    jobs = jobs.filter((j) =>
      `${j.title} ${j.company} ${j.location}`.toLowerCase().includes(s)
    );
  }
  res.json(jobs);
});

app.patch('/api/leads/:id', (req, res) => {
  const jobs = read('jobs.json');
  const job = jobs.find((j) => j.id === req.params.id);
  if (!job) return res.status(404).json({ error: 'Lead not found' });
  for (const field of ['status', 'contact', 'phone', 'notes']) {
    if (field in req.body) job[field] = String(req.body[field]);
  }
  write('jobs.json', jobs);
  res.json(job);
});

app.post('/api/refresh', async (req, res) => {
  const result = await refreshJobs();
  res.json(result);
});

app.get('/api/candidates', (req, res) => res.json(read('candidates.json')));

app.post('/api/apply', upload.single('cv'), (req, res) => {
  const { name, email, phone, sector, message } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required.' });
  }
  const candidates = read('candidates.json');
  candidates.unshift({
    id: randomUUID(),
    name: String(name),
    email: String(email),
    phone: phone ? String(phone) : '',
    sector: sector ? String(sector) : 'other',
    message: message ? String(message) : '',
    cvFile: req.file ? req.file.filename : '',
    cvOriginalName: req.file ? req.file.originalname : '',
    received: new Date().toISOString()
  });
  write('candidates.json', candidates);
  res.json({ ok: true });
});

// ---------- start ----------
app.listen(PORT, async () => {
  console.log(`\n  Lumora API running  ->  http://localhost:${PORT}\n`);
  if (isLive()) {
    console.log(`  Mode: LIVE (Adzuna keys detected). Auto-check every ${POLL_MINUTES} min.\n`);
  } else {
    console.log('  Mode: SAMPLE (no Adzuna keys). Showing example data only.');
    console.log('  Add keys in a .env file to pull real jobs - see SETUP.md.\n');
  }
  await refreshJobs();
  if (isLive()) setInterval(() => refreshJobs(), POLL_MINUTES * 60 * 1000);
});
