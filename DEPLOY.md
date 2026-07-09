# Running Educator for friends over the internet

`./run.sh --web` runs the app in **multi-user mode behind a tunnel**: everyone
logs in with their own account (separate progress), the app listens on
`localhost` only, cookies are HTTPS-safe, and **public sign-ups are closed** —
you create the accounts. You put a tunnel (ngrok, Cloudflare, …) in front to
give it a public HTTPS URL. Nothing about the app is tied to a specific tunnel.

## 1. Create accounts (one-time, per person)

Sign-ups are closed in `--web` mode, so provision each friend yourself:

```bash
cd backend
../.venv/bin/python -m app.manage create-user alice      # prompts for a password
../.venv/bin/python -m app.manage list-users
../.venv/bin/python -m app.manage set-password alice     # reset a password
../.venv/bin/python -m app.manage delete-user alice      # remove account + progress
```

Hand each person their username and password out-of-band (text, in person, …).

## 2. Serve it

```bash
./run.sh --web
```

This builds the frontend and serves on `http://127.0.0.1:8700` (local only).

## 3. Expose it with your tunnel

In a second terminal, point your tunnel at port 8700 and share the HTTPS URL it
prints:

```bash
ngrok http 8700
```

Your friends open the `https://….ngrok…` URL, log in, and go. That's it.

### Other tunnels (all work the same — no code changes)

- **Cloudflare Quick Tunnel** — free, no account, ephemeral URL:
  `cloudflared tunnel --url http://localhost:8700`
- **Cloudflare Named Tunnel** — free tunnel + a domain you own (~$10–15/yr),
  gives a permanent `educator.yourdomain.com`. See Cloudflare's Zero Trust docs.
- **Tailscale Funnel** — free on personal, stable public `*.ts.net` URL, no
  domain needed: `tailscale funnel 8700`

## Notes & limits

- **This is for a handful of trusted people.** SQLite + a single worker is fine
  at that scale; book ingestion is heavy (it runs LLM jobs on this machine), so
  concurrent uploads will contend for the GPUs.
- **Security posture:** login/registration are rate-limited per client, the
  session cookie is `HttpOnly` + `Secure`, and the app trusts `X-Forwarded-*`
  from the tunnel (`--proxy-headers`). It does **not** run its own TLS — the
  tunnel terminates HTTPS. Keep the tunnel URL among people you trust.
- **Backups:** the SQLite DB lives in `data/` and is backed up to
  `data/backups/` automatically before each schema migration.
- To take it down, stop the tunnel and `Ctrl-C` the server.
