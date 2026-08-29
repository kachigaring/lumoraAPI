# Emailing the daily lists

The engine can email the CSVs to **aisha@lumorarecruitment.com** every time it
runs. It sends them *through* a mailbox you own, using a one-time "App Password"
(a special password just for programs - not your normal login).

You only do this once.

---

## If lumorarecruitment.com is on Google Workspace (Gmail)

1. Sign in to that mailbox, go to **myaccount.google.com**.
2. **Security** -> make sure **2-Step Verification** is ON (turn it on if not).
3. Search the page for **App passwords** (or go to
   myaccount.google.com/apppasswords).
4. Create one, name it "Lumora engine". Google shows a **16-letter password**
   like `abcd efgh ijkl mnop`. Copy it (you can ignore the spaces).

When `run_client_leads.bat` asks on first run:
- **Address the email is SENT FROM:** `aisha@lumorarecruitment.com`
- **App Password:** paste the 16 letters

That's it.

## If the mailbox is somewhere else (Outlook / Microsoft 365, a host, etc.)

Open `engine\.env` in Notepad and set these four lines to your provider's
outgoing (SMTP) details:

```
SMTP_HOST=smtp.office365.com        (example for Microsoft 365)
SMTP_PORT=587
SMTP_USER=aisha@lumorarecruitment.com
SMTP_PASSWORD=your-app-password
```

Your email provider's help pages list the "SMTP server" name and port.

## To change it later

Edit `engine\.env` in Notepad. To send the report somewhere else too, change
`REPORT_TO`. To stop emails, blank out `REPORT_TO`.

## Nothing happens?

The run still saves every file in `engine\output\`. If the email fails, the
black window prints why - usually the App Password is wrong or 2-Step
Verification isn't on.
