# Putting Lumora online with Render

This makes the tool reachable from a web address instead of only your own PC.
Render connects to your GitHub repo and rebuilds every time you push.

Time: about 15 minutes. No card needed for the free plan.

---

## Before you start

Decide your **admin login** now — a username and a strong password. You'll paste
them into Render in step 4. This login protects the leads board and the CV list.
The public application form does **not** need it.

---

## Step 1 — Create the service

1. Go to <https://dashboard.render.com> and sign in with GitHub.
2. Click **New** → **Web Service**.
   (Not "Static Site" — that can't run the server. Not "Private Service" — that
   isn't reachable from the internet.)
3. Choose the **`kachigaring/lumoraAPI`** repository → **Connect**.

## Step 2 — Settings

Render fills most of this in from the repo. Check these values:

| Field | Value |
| --- | --- |
| Name | `lumora-api` (this becomes the web address) |
| Region | Whatever is closest (e.g. Frankfurt) |
| Branch | `main` |
| Runtime | `Node` |
| Build Command | `npm install` |
| Start Command | `npm start` |
| Instance Type | **Free** to start |

## Step 3 — (skip) Advanced

Leave the rest as default.

## Step 4 — Environment variables

Scroll to **Environment Variables** and add these (click **Add** for each):

| Key | Value |
| --- | --- |
| `ADMIN_USER` | the username you chose |
| `ADMIN_PASSWORD` | the password you chose |
| `ADZUNA_APP_ID` | from developer.adzuna.com (or leave out for now) |
| `ADZUNA_APP_KEY` | from developer.adzuna.com (or leave out for now) |

You do **not** need to set `PORT` — Render sets it automatically.

## Step 5 — Create

Click **Create Web Service**. The first build takes 2–4 minutes. When it says
**Live**, click the address at the top — it looks like:

```
https://lumora-api.onrender.com
```

- `https://lumora-api.onrender.com/` — the leads board (asks for your login)
- `https://lumora-api.onrender.com/apply.html` — the public form for candidates
- `https://lumora-api.onrender.com/candidates.html` — the CV list (asks for your login)

---

## Step 6 — Link it from your Odoo site

On `lumoraapi.odoo.com`, edit the page and add a button or link pointing to
`https://lumora-api.onrender.com/apply.html`. That's the only part of the tool
the public should reach. Keep the board address for yourself.

---

## Things to know about the free plan

- **It sleeps.** After 15 minutes with no visitors it goes to sleep; the next
  visit takes ~50 seconds to wake up, then it's fast again.
- **Storage is temporary.** Every time Render rebuilds or restarts, the saved
  leads, your call notes, and **uploaded CV files are wiped**. Job listings
  refill by themselves from Adzuna; your notes and the CVs do not.

### When you're ready to rely on it

Two options, pick one:

1. **Simplest:** upgrade the service to **Starter** (about US$7/month) and add a
   **Disk** (1 GB) mounted at `/opt/render/project/src/data`. Storage then
   survives restarts. (Render disks aren't available on the Free plan.)
2. **Bigger change:** move storage to a database + file storage. More work — ask
   for help when you get to this point.

Until then, treat the online version as a **live demo and public form**, and if
you're collecting real CVs, also have applicants emailed to you as a backup.

---

## Updating the site later

Any change that gets pushed to the `main` branch on GitHub makes Render rebuild
and redeploy automatically. Nothing else to do.
