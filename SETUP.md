# Setting up Lumora for the first time

Written for someone who has **never written code**. Do the steps in order.
About 15 minutes.

---

## Step 1 — Install Node.js

Node.js is the free engine this tool runs on.

1. Go to <https://nodejs.org>
2. Click the button labelled **"LTS"**.
3. Open the downloaded file and click **Next → Next → Install** (defaults are fine).
4. Restart the computer if it asks.

**Check it worked:** press the Windows key, type `cmd`, open **Command Prompt**,
type `node -v` and press Enter. You should see something like `v20.17.0`.
If you get "not recognized", Node isn't installed yet — redo this step and restart.

---

## Step 2 — The Lumora folder

It's already on this PC at:

```
C:\Users\Dell XPS\Documents\lumoraAPI
```

If you ever re-download it from GitHub as a ZIP: right-click the ZIP →
**Extract All** → use the folder that appears inside.

---

## Step 3 — Start it

1. Open the `lumoraAPI` folder in File Explorer.
2. Double-click **`start.bat`**.
3. A black window opens. The **first** run spends a minute installing things —
   leave it alone.
4. When you see:

   ```
   Lumora API running  ->  http://localhost:3000
   ```

   open your browser and go to **http://localhost:3000**

You'll see the Leads board with a few example jobs and an orange
**"SAMPLE DATA"** badge. That means everything works — it just isn't pulling
real jobs yet. Step 4 fixes that.

- **To stop it:** close the black window.
- **Next time:** just double-click `start.bat` again (no wait, it won't reinstall).

---

## Step 4 — Turn on real jobs (free Adzuna key)

Adzuna is a job search engine that lets you pull listings for free.

1. Go to <https://developer.adzuna.com/> and click **Sign up**. Confirm your email.
2. Your dashboard shows an **Application ID** and an **Application Key**.
3. In the `lumoraAPI` folder, find **`.env.example`**.
4. **Copy** that file (Ctrl+C, Ctrl+V in the same folder). Rename the copy to
   exactly:

   ```
   .env
   ```

   No text before the dot. No `.txt` on the end. If Windows hides the ending:
   in File Explorer, View menu → tick **File name extensions**.
5. Open `.env` in Notepad and fill in the two lines:

   ```
   ADZUNA_APP_ID=your-application-id
   ADZUNA_APP_KEY=your-application-key
   ```

6. Save and close. Close the black window if it's running, then double-click
   `start.bat` again.

The badge should now be green: **"LIVE — pulling real jobs"**. It checks on
startup and then every 15 minutes. The **"Check for new jobs"** button forces
a check straight away.

---

## Using the board day to day

- **Filter** by sector (start with *Nursery / Early Years*) and by status.
- After a call, set the **Status** dropdown: New → Calling today → Called → etc.
  It saves by itself.
- Type the **HR manager's name and phone** into the contact boxes as you find them.
- Use **Notes** for what was said and call-back times.
- Click a **job title** to open the original advert.

## The CV side

- Give candidates this link **while the tool is running**:
  `http://localhost:3000/apply.html`
- Their submissions show up on the **CV database** page, each with a link to
  download the CV file.
- (Later step: host the form online so people can use it any time, not only
  when your PC is on.)

## Tuning nursery and biomed

Open `src/sectors.js` in Notepad. For each sector there are:

- `queries` — the exact phrases sent to the job search
- `keywords` — words that tag a job as that sector

Add or change phrases, save, restart `start.bat`. Start with nursery; leave
biomed as-is until nursery is giving good results.

---

## Keep private data private

This project is linked to a **public** GitHub page. It's already set up so your
`.env` key, the collected CVs, and your lead notes are **never uploaded** there
(they stay in the `data/` folder, which Git ignores). Don't move those files out
of `data/`.

---

## If something goes wrong

| Problem | Fix |
| --- | --- |
| `'node' is not recognized` | Node.js not installed, or PC not restarted. Redo Step 1. |
| `'npm' is not recognized` | Same as above. |
| Black window flashes then vanishes | Open Command Prompt, drag `start.bat` into it, press Enter, read the error. |
| Badge stays orange after adding the key | File must be named `.env` exactly; keys pasted with no spaces or quotes; restart. |
| `EADDRINUSE` / port 3000 in use | Open `.env`, change `PORT=3000` to `PORT=3001`, use http://localhost:3001 |
| Adzuna errors in the black window | Free tier has a monthly limit; check your keys are correct on the Adzuna dashboard. |
