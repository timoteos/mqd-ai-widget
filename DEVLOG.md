# Dev Log

Newest first. Timestamps pulled from git history.

## 2026-11-10 15:03 — Eligibility estimate, worked out in code (temporary figures)

Added for the demo. The live Lambda already runs this version.

- The five eligibility questions now end in an estimate: the income limit
  for the household and whether the income is under or over it. The
  comparison is done in `lambda_function.py`, not by the model, so the same
  answers always give the same result. The model had been reading the wrong
  row of the income chart.
- Over the limit never gets a "no": it says the person may still qualify
  another way and should apply. If household size or income cannot be read
  as a number, there is no estimate and the old "apply to find out" reply
  is used.
- Questions about yourself ("would I qualify?", "do we qualify?") now start
  the five questions. General questions that contain the word do not.

**The figures are not verified.** They are calculated from the 2025 Hawaii
poverty guideline and these percentages: adults 19-64 138%, children 313%,
pregnant 196%, 65 and over 100%. Only three were matched against the chart
(adults, households of 1 and 2; 65 and over, household of 1). Med-QUEST
staff need to check them and supply the current year's before real use.

**Not done:** the estimate is English only; the bot asks for household size
and income again even when the first question gave them; "me and my 2 kids"
is read as 2 people; there is no way out of the questions part-way through;
asked afterwards to repeat the limit, the bot refuses.

## 2026-11-10 15:05 — Answers open at their first line; test page chat fixed

- After a reply arrives the chat scrolls to the top of the answer instead of
  the bottom, so a long answer is read from its first line. Short answers
  still sit at the bottom.
- The plain test page (`/demo`) had the chat address hardcoded to
  `localhost:3000`, so every question failed on any other port or host. It
  now uses the address the page is served from.

## 2026-11-10 14:40 — Showcase page rebuilt as a recording of the new site

medquest.hawaii.gov was rebuilt (Adobe AEM to Next.js), so every stylesheet
and image the replica borrowed from it stopped loading and the page showed as
unstyled HTML.

- `/` is now a recording of the new home page: its HTML plus the stylesheets,
  scripts, font and images it loads, saved in `website/live` and served by
  `server.js` at the addresses the page asks for. The menus and the carousel
  work, and it does not depend on the live site. Only the home page was
  recorded, so a link to any other page opens the real site in a new tab.
- `/screenshot` is the fallback: a picture of the home page
  (`website/medquest-home.jpg`) with the widget on top. Nothing on it is
  clickable, and nothing on it can break.
- Cloudflare's scripts (analytics, bot checks) were removed from the
  recording. The site's own accessibility button still loads from its vendor.

Both have to be retaken if the site's look changes. The recording was made
with headless Chrome over the DevTools protocol, because the site refuses
requests that do not come from a browser.

## 2026-11-10 14:10 — Backend outage, guardrail blocks, eligibility answers

**Outage (fixed in AWS, not in code):** every question failed with a 500
error. The knowledge base's IAM role, shared with the internal ikebot, had
been changed to allow only ikebot's vector index (`mqd-internal-vectors`).
The role now lists both indexes. Giving each bot its own role would stop
this happening again.

**Lambda (`lambda_function.py`):**
- Guardrail blocks show a friendly message with the phone number instead of
  "Sorry, this question could not be answered.", and guardrail tracing is on
  (search the logs for `GUARDRAIL INTERVENED`).
- The SSN filter no longer hides the ZIP+4 in Med-QUEST's address, and
  hawaii.gov emails show in answers.
- Prompt cleanup: no "I appreciate the test", no mentions of "the documents",
  neutral wording about income.
- The bot no longer states income limits or says whether someone is likely
  to qualify. It kept quoting the wrong row of the income chart (the
  2-person limit for a household of 3), which tells families who qualify
  that they don't. A version that searched harder for the chart made the
  figures inconsistent and was rolled back.

**Widget:** markdown lists render properly (no more "double spacing"), the
host page's letter-spacing no longer leaks in, and the input box opens at
its full height.

**Left for later:** the guardrail still blocks about 4 in 10 conversations
that include personal details (users see the friendly message); follow-up
questions often fail; sources are never returned; Ilocano replies are
garbled; official income limits should be built into the code and checked
by Med-QUEST staff.

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
