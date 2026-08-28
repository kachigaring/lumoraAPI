# lumoraAPI

A private tool for spotting fresh job vacancies fast and turning them into sales
leads — plus a place to collect candidate CVs.

## What it does

- **Job-lead board** — checks job sites for vacancies posted in the last day or
  two and lists them newest-first, so you can ring the employer's HR team while
  the advert is still warm. Every row has a **Status** (New, Calling today,
  Called, Left message…), **HR contact / phone** boxes and a **Notes** box, so
  the board doubles as your call sheet. Changes save automatically.
- **Sector focus** — tuned for **Nursery / Early Years** first and
  **Biomedical Science** second, but it will pick up any role you search for.
- **CV database** — a public application form (`/apply.html`) where candidates
  send their details and upload a CV. Everything received is listed on the
  **CV database** page with a download link.

It runs on your own computer. Nothing is shared publicly unless you host it
somewhere later.

## Quick start

If Node.js is already installed: double-click **`start.bat`**, wait for
`running`, then open <http://localhost:3000>.

**Never done this before?** Follow **[SETUP.md](SETUP.md)** — it starts from
installing Node.js and assumes no coding experience.

## Two modes

| Mode | When | What you see |
| --- | --- | --- |
| **Sample** | No Adzuna key yet | A few example jobs, so you can see the layout |
| **Live** | Adzuna key added to `.env` | Real vacancies, refreshed automatically |

A free Adzuna key takes about 5 minutes to get — SETUP.md step 4.

## What's in the folder

| Path | What it is |
| --- | --- |
| `start.bat` | Double-click to run the tool |
| `server.js` | The web server |
| `src/sectors.js` | The search terms + tags for each sector — **edit this to tune nursery/biomed** |
| `src/jobs.js` | Talks to the Adzuna job API |
| `public/` | The pages you see in the browser |
| `data/` | Your leads, notes and CVs live here (kept off GitHub) |
| `.env.example` | Copy to `.env` and add your Adzuna key |

## Roadmap

- [ ] Tune nursery search terms against real results
- [ ] Add biomed once nursery is working
- [ ] Look up HR phone numbers automatically
- [ ] Email/desktop alert when a new nursery job lands
- [ ] Host the apply form online so candidates can reach it any time
