// Fetches fresh vacancies from Adzuna (free job-search API) and stores the new
// ones. If no Adzuna keys are set, it stays in "sample" mode and does nothing.
import 'dotenv/config';
import { SECTORS, detectSector } from './sectors.js';
import { read, write } from './store.js';

const APP_ID = process.env.ADZUNA_APP_ID;
const APP_KEY = process.env.ADZUNA_APP_KEY;
const COUNTRY = process.env.ADZUNA_COUNTRY || 'gb';
const MAX_DAYS_OLD = Number(process.env.MAX_DAYS_OLD || 2);

export function isLive() {
  return Boolean(APP_ID && APP_KEY);
}

function stripTags(s = '') {
  return String(s).replace(/<\/?[^>]+>/g, '').trim();
}

function formatSalary(r) {
  if (!r.salary_min || r.salary_is_predicted === '1') return '';
  const min = `£${Math.round(r.salary_min).toLocaleString()}`;
  if (r.salary_max && Math.round(r.salary_max) !== Math.round(r.salary_min)) {
    return `${min}–£${Math.round(r.salary_max).toLocaleString()}`;
  }
  return min;
}

export async function refreshJobs({ log = console.log } = {}) {
  const jobs = read('jobs.json');

  if (!isLive()) {
    log('[jobs] No Adzuna keys set — SAMPLE mode, no live fetch.');
    return { mode: 'sample', added: 0, total: jobs.length };
  }

  const seen = new Set(jobs.map((j) => j.id));
  let added = 0;

  for (const [sectorKey, cfg] of Object.entries(SECTORS)) {
    for (const phrase of cfg.queries) {
      const url =
        `https://api.adzuna.com/v1/api/jobs/${COUNTRY}/search/1` +
        `?app_id=${encodeURIComponent(APP_ID)}` +
        `&app_key=${encodeURIComponent(APP_KEY)}` +
        `&results_per_page=50&sort_by=date&max_days_old=${MAX_DAYS_OLD}` +
        `&what=${encodeURIComponent(phrase)}` +
        `&content-type=application/json`;

      try {
        const res = await fetch(url);
        if (!res.ok) {
          log(`[jobs] Adzuna returned ${res.status} for "${phrase}"`);
          continue;
        }
        const data = await res.json();
        for (const r of data.results || []) {
          const id = `adzuna-${r.id}`;
          if (seen.has(id)) continue;
          seen.add(id);

          const blob = `${r.title} ${r.description || ''} ${r.category?.label || ''}`;
          const detected = detectSector(blob);

          jobs.push({
            id,
            source: 'Adzuna',
            title: stripTags(r.title) || 'Untitled role',
            company: r.company?.display_name || 'Unknown employer',
            location: r.location?.display_name || '',
            salary: formatSalary(r),
            url: r.redirect_url || '',
            posted: r.created || new Date().toISOString(),
            found: new Date().toISOString(),
            sector: detected === 'other' ? sectorKey : detected,
            status: 'New',
            contact: '',
            phone: '',
            notes: ''
          });
          added++;
        }
      } catch (err) {
        log(`[jobs] fetch failed for "${phrase}": ${err.message}`);
      }
    }
  }

  jobs.sort((a, b) => String(b.posted || '').localeCompare(String(a.posted || '')));
  write('jobs.json', jobs);
  log(`[jobs] Live refresh done — ${added} new, ${jobs.length} total.`);
  return { mode: 'live', added, total: jobs.length };
}
