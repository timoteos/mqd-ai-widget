const fs = require("fs");
const path = require("path");
const express = require("express");
const dotenv = require("dotenv");

dotenv.config({ path: path.join(__dirname, ".env") });

const app = express();
const port = Number(process.env.PORT || 3000);
const chatApiUrl = process.env.CHAT_API_URL;
const requestTimeoutMs = Number(process.env.REQUEST_TIMEOUT_MS || 90000);

app.use(express.json({
  limit: "1mb",
  verify: (req, _res, buf) => {
    req.rawBody = buf.toString("utf8");
  }
}));
app.get(["/", "/index.html"], (_req, res) => {
  res.sendFile(path.join(__dirname, "website", "index.html"));
});

app.get("/demo", (_req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// The showcase page before it was a recording: a picture of the home page with
// the widget on top. Kept as a fallback, because a picture cannot break.
app.get("/screenshot", (_req, res) => {
  res.sendFile(path.join(__dirname, "website", "screenshot.html"));
});

// The showcase page at "/" is a recording of medquest.hawaii.gov's home page.
// Its stylesheets, scripts, fonts and images were recorded with it and are
// served from here at the addresses the page asks for, so the page does not
// depend on the live site. The site's file names change on every deploy, and
// it refuses requests that do not come from a browser, so neither linking to
// its files nor fetching them from this server works.
const recordedDir = path.join(__dirname, "website", "live");
const recorded = fs.existsSync(path.join(recordedDir, "manifest.json"))
  ? JSON.parse(fs.readFileSync(path.join(recordedDir, "manifest.json"), "utf8"))
  : {};

// An image was recorded at the sizes the recording browser asked for. A
// different screen asks for a different size, so fall back to the largest
// recorded copy of the same image, and to the same path with another query.
const imageSource = (address) => new URL(address, "http://localhost").searchParams.get("url");
const imageWidth = (address) => Number(new URL(address, "http://localhost").searchParams.get("w")) || 0;

function findRecorded(req) {
  if (recorded[req.originalUrl]) return recorded[req.originalUrl];
  const keys = Object.keys(recorded);
  if (req.path === "/_next/image") {
    const source = imageSource(req.originalUrl);
    const sizes = keys
      .filter((key) => key.startsWith("/_next/image?") && imageSource(key) === source)
      .sort((x, y) => imageWidth(y) - imageWidth(x));
    return sizes.length ? recorded[sizes[0]] : null;
  }
  const samePath = keys.find((key) => key.split("?")[0] === req.path);
  return samePath ? recorded[samePath] : null;
}

app.get("*", (req, res, next) => {
  const hit = findRecorded(req);
  if (!hit) return next();
  res.type(hit.type);
  res.sendFile(path.join(recordedDir, hit.file));
});

app.use(express.static(path.join(__dirname), { index: false }));

app.post("/widget-api/chat", async (req, res) => {
  try {
    if (!chatApiUrl) {
      return res.status(500).json({
        answer: "Chat API is not configured on the backend. Set CHAT_API_URL in .env.",
        sources: []
      });
    }

    const { question, user_id, session_id } = req.body;
    const questionText = typeof question === "string" ? question.trim() : "";
    if (!questionText) {
      return res.status(400).json({
        answer: "Question is required.",
        sources: []
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

    let upstream;
    try {
      upstream = await fetch(chatApiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: req.rawBody || JSON.stringify({
          question: questionText,
          user_id,
          session_id,
        }),
        signal: controller.signal
      });
    } catch (error) {
      if (error && error.name === "AbortError") {
        return res.status(504).json({
          answer: `API timed out after ${requestTimeoutMs}ms. Please try again.`,
          sources: []
        });
      }

      return res.status(502).json({
        answer: "API is currently unreachable. Please try again later.",
        sources: []
      });
    } finally {
      clearTimeout(timeoutId);
    }

    let data;
    try {
      data = await upstream.json();
    } catch {
      return res.status(502).json({
        answer: "API returned invalid JSON.",
        sources: []
      });
    }

    const answer = typeof data?.answer === "string"
      ? data.answer
      : "API response format is invalid. Expected an 'answer' string.";
    const sources = Array.isArray(data?.sources) ? data.sources : [];

    if (!upstream.ok) {
      return res.status(upstream.status).json({
        answer: `API request failed with status ${upstream.status}.`,
        sources
      });
    }

    return res.json({ answer, sources });
  } catch {
    return res.status(500).json({
      answer: "Unexpected server error while processing chat request.",
      sources: []
    });
  }
});

app.listen(port, () => {
  console.log(`MQD AI Widget server running at http://localhost:${port}`);
});
