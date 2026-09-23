# Dev Log

Newest first. Timestamps pulled from git history.

## 2026-09-23 11:17 — Landing page replica for showcasing the widget

Added `website/index.html`, a snapshot of medquest.hawaii.gov's actual landing
page markup with every root-relative link/asset URL rewritten to absolute
`https://medquest.hawaii.gov/...` URLs. All images, CSS, and fonts load live
from the real site rather than being copied locally, so it stays visually
exact with no asset maintenance — the tradeoff is it needs internet access to
render fully. Dropped the Google Analytics and Constant Contact scripts since
they're not relevant to a local demo.

`npm start` now serves this replica at `/` with the widget embedded, so it can
be shown next to the real site for comparison. The original blank
config-tester page moved to `/demo`.

## 2026-09-23 11:01 — Widget UX pass + match medquest.hawaii.gov's visual style

- Added a disclaimer noting the assistant gives general info, not official
  Med-QUEST determinations.
- Added a Retry button on failed requests that resends the same question.
- Added thumbs up/down feedback on assistant answers (logged client-side for
  now — no feedback endpoint exists yet).
- Made the chat log an `aria-live` region and labeled the typing indicator for
  screen readers.
- Added a clear-conversation button that resets the chat and generates new
  session/user IDs.
- Restyled colors and typography to match medquest.hawaii.gov's actual
  palette (teal `#208380` / olive `#608000` brand accents, its text/
  background/border colors, Source Sans Pro) — pulled directly from the
  site's production CSS instead of guessing, replacing the generic
  blue/green placeholder theme.

## 2026-08-28 08:49 — Repo cleanup

Removed a `.DS_Store` file that had been accidentally committed and added it
to `.gitignore`.

## 2026-08-26 10:33 — Typing indicator

Added an animated three-dot "typing" bubble that appears in the chat log
while waiting on the API, replacing the plain "Waiting for response..."
status text as the only feedback.

## 2026-07-02 — Initial setup

- Initial commit of the widget (Express server, demo page, `widget.js`/
  `widget.css`, and the Lambda backend function).
- `.env` (holding `CHAT_API_URL`) was briefly committed for convenience when
  setting up on another machine, then removed and re-added to `.gitignore`.
- Repo pushed to GitHub at `timoteos/mqd-ai-widget` (private).

## Left untouched

- No backend feedback endpoint — thumbs up/down votes are only logged to the
  browser console right now.
- No conversation persistence — refreshing the page still starts a brand new
  session.
- Admin/auth, rate limiting, and streaming responses were discussed but not
  built.
