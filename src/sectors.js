// Which sectors we chase, the phrases we search job sites for,
// and the words we use to tag a job once we have it.
// Add more sectors here later (teaching, care, pharma...) — the rest of the
// app picks them up automatically.

export const SECTORS = {
  nursery: {
    label: 'Nursery / Early Years',
    queries: [
      'nursery nurse',
      'nursery practitioner',
      'early years practitioner',
      'nursery manager',
      'nursery room leader'
    ],
    keywords: [
      'nursery', 'early years', 'eyfs', 'preschool', 'pre-school', 'childcare',
      'nursery nurse', 'nursery practitioner', 'room leader', 'key person',
      'early years practitioner', 'nursery manager', 'day nursery', 'childminder'
    ]
  },
  biomed: {
    label: 'Biomedical Science',
    queries: [
      'biomedical scientist',
      'biomedical support worker',
      'medical laboratory assistant'
    ],
    keywords: [
      'biomedical scientist', 'biomedical science', 'biomedical support', 'bms',
      'hcpc', 'pathology', 'haematology', 'histology', 'microbiology',
      'blood sciences', 'medical laboratory', 'laboratory assistant', 'cytology',
      'transfusion', 'immunology', 'clinical laboratory', 'phlebotomy'
    ]
  }
};

/** Best-guess sector for a chunk of job text. Returns 'other' if nothing matches. */
export function detectSector(text = '') {
  const t = String(text).toLowerCase();
  for (const [key, cfg] of Object.entries(SECTORS)) {
    if (cfg.keywords.some((k) => t.includes(k))) return key;
  }
  return 'other';
}
