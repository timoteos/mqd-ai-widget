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
app.use(express.static(path.join(__dirname)));

app.get(["/", "/index.html"], (_req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

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
