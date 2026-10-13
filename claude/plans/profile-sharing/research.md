# Profile sharing: research (2026-10-13, planning only)

User: "I want to create a profile upload/download in the application ... for people to upload/download profile packages from the application" / "how about if the app pushes the document to me, for approval first?" / "what about discord?" / "do research on the internet about small apps trying this and see what service is best for us to use".

Three parallel research agents (R-APPS, R-SERVICES, R-DISCORD), 2026-10-13.

## Rule that drives the design
The app cannot hold a secret (tokens, passwords, webhook URLs can be extracted from a shipped program). Uploads must go to something that accepts them without the app holding write credentials; approval and publishing happen server-side.

## How other apps do it (R-APPS)
- No small open-source app found with in-app, account-free upload + owner approval. Closest: Lutris (human approval, account needed), OpenTabletDriver (in-app plugin browser reading a GitHub metadata repo with URL + SHA256 per entry; submissions by GitHub PR).
- Working catalogues hold uploads pending until a human approves: flightsim.to (Pending/Approved/Declined), mod.io Full Curation, OBS, Lutris. SimHub's open forum had to pause sign-ups for spam.
- Config zips carried malware elsewhere (Rainmeter on DeviantArt, Thunderstore): accept only expected file types, reject executables/scripts, cap size, check zip contents server-side.
- Auto-scanning gives false positives (Nexus quarantine); owner makes the final call; uploader sees status.
- Central store + per-file hash (OpenTabletDriver) beats forum/Discord link rot (VoiceAttack, TARGET, JoyToKey, Joystick Gremlin today).
- Cloudflare publishes a reference design for exactly this: Worker validates, signed upload to a private R2 area, D1 records, approval moves to public listing.
  https://developers.cloudflare.com/reference-architecture/diagrams/storage/storing-user-generated-content/

## Discord facts (R-DISCORD, official docs fetched 2026-10-13)
- Attachment links are signed and expire (since late 2023); refreshing needs a bot/user token. Not a stable download store.
- Default upload limit 20 MiB (raised Aug 2026; was 10 MB from Sep 2024), webhooks included.
- Anyone holding a webhook URL can post AND delete the webhook without authentication (Delete Webhook with Token). A webhook URL shipped in the app lets one person disable uploads for every install. Security vendors treat webhook URLs as secrets.
- Forum channel + bot tags work for review, but files still need a permanent home elsewhere.

## Services compared (R-SERVICES)
| Option | Anonymous upload | Approval | Download | Free at our scale | Notes |
|---|---|---|---|---|---|
| GitHub repo/Releases | no (needs token) | PR review if a server opens it | Releases fine; raw.githubusercontent anonymous limits tightened May 2025, unpublished | free | good as a public mirror, not the upload path |
| Cloudflare Workers + R2 | yes via Worker | own (pending -> approved) | R2, no egress fees | R2 10 GB, 1M writes, 10M reads/month; Workers 100k req/day, 100 MB/request | Turnstile needs a web page; start with rate limits + caps + approval; S3-compatible (easy to leave) |
| Supabase | yes (anon key + insert-only rule) | own | CDN | 1 GB storage, 5 GB egress; free projects pause after a week idle | pause is a problem |
| Firebase | possible | own | CDN | storage needs paid Blaze plan from Feb 2026; no Windows App Check | poor fit |
| mod.io | no (email login token needed) | built-in curation | good | pricing/non-game eligibility unconfirmed | fallback if email login is OK |
| Backblaze B2 | needs a signing function | own | free egress via Cloudflare | 10 GB | same as R2 but needs a function elsewhere |
| Netlify/Vercel | yes | own | fine | credits / 4.5 MB body cap on Vercel | weaker fit |
| itch.io | no | - | - | - | not suitable |

Unverified: mod.io pricing/eligibility; GitHub raw limits; some R2/Workers/Turnstile figures came from mirrors — check live pricing pages before deciding.

## Recommendation (to the user, not decided)
Cloudflare Worker + R2: app posts zip to the Worker (size/zip/layout checks, per-IP rate limit, daily cap) -> R2 pending/ -> owner approves (small admin page or command line with a secret only the owner holds) -> moved to approved/, index.json rebuilt -> app downloads index.json, searches locally, downloads packages and checks SHA256. Optional: approval also publishes a copy to a GitHub repo/release for public history. Discord only as a notification/community channel fed by the Worker (webhook URL kept in the Worker, never in the app).
