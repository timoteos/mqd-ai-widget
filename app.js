const endpointInput = document.getElementById("endpoint");
const mockModeInput = document.getElementById("mockMode");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("question");
const chatLog = document.getElementById("chat");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const requestDump = document.getElementById("requestDump");
const responseDump = document.getElementById("responseDump");
const messageTemplate = document.getElementById("messageTemplate");
const controlsPanel = document.querySelector(".controls-panel");

let currentSessionId = null;
let currentUserId = null;

function generateId() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ensureSessionIdentity() {
  if (!currentUserId) {
    currentUserId = generateId();
  }

  if (!currentSessionId) {
    currentSessionId = generateId();
  }
}

const sessionStatusEl = document.createElement("small");
sessionStatusEl.id = "sessionStatus";
controlsPanel.appendChild(sessionStatusEl);

function updateSessionStatus() {
  if (currentSessionId && currentUserId) {
    sessionStatusEl.textContent = `User ID: ${currentUserId} | Session ID: ${currentSessionId}`;
  } else {
    sessionStatusEl.textContent = "Session ID: (new conversation)";
  }
}

ensureSessionIdentity();
updateSessionStatus();

const STORAGE_KEY = "api-chat-tester-endpoint";
const REQUEST_TIMEOUT_MS = 90000;
const DEFAULT_SAMPLE_RESPONSE = {
  answer: "### Welcome to Med-QUEST\\n\\nThis is the Hawaii Department of Human Services (DHS) Med-QUEST website.",
  sources: [
    "digital-experience-KB/general-medicaid-eligibility/Quest_Member.Handbook_2025_FINAL.pdf",
    "digital-experience-KB/medquest-forms/MQD-termination-form.pdf",
    "digital-experience-KB/medquest-forms/DHS-1125.pdf"
  ]
};

endpointInput.value = localStorage.getItem(STORAGE_KEY) || "";

function renderMarkdown(text) {
  const raw = typeof text === "string" ? text : String(text ?? "");

  if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
    const html = marked.parse(raw, { breaks: true, gfm: true });
    return DOMPurify.sanitize(html);
  }

  const escaped = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");

  return escaped;
}

function appendMessage(role, bodyText, sources) {
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  node.querySelector(".message-header").textContent =
    role === "user" ? "Question" : role === "assistant" ? "Answer" : "Error";

  const body = node.querySelector(".message-body");
  if (role === "assistant") {
    body.innerHTML = renderMarkdown(bodyText);
  } else {
    body.textContent = bodyText;
  }

  if (Array.isArray(sources) && sources.length > 0) {
    const label = document.createElement("p");
    label.textContent = "Sources:";
    label.className = "sources-label";

    const list = document.createElement("ul");
    for (const source of sources) {
      const item = document.createElement("li");
      item.textContent = source;
      list.appendChild(item);
    }
    body.appendChild(document.createElement("hr"));
    body.appendChild(label);
    body.appendChild(list);
  }

  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setLoading(isLoading) {
  sendBtn.disabled = isLoading;
  sendBtn.textContent = isLoading ? "Waiting for API response..." : "Send Question";
}

function updateDebugPanels(requestObj, responseObj) {
  requestDump.textContent = JSON.stringify(requestObj, null, 2);
  responseDump.textContent = JSON.stringify(responseObj, null, 2);
}

async function fetchAnswer(payload) {
  // The session_id from the payload is for the *request*.
  // The one from the response will be used for the *next* request.
  if (mockModeInput.checked) {
    return {
      ...DEFAULT_SAMPLE_RESPONSE,
      session_id: payload.session_id || crypto.randomUUID(),
      user_id: payload.user_id || crypto.randomUUID()
    };
  }

  const endpoint = endpointInput.value.trim();
  if (!endpoint) {
    throw new Error("Please enter an API endpoint or turn on mock mode.");
  }

  localStorage.setItem(STORAGE_KEY, endpoint);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("API did not respond within 90 seconds. Please try again.");
    }
    throw new Error("API is not working right now. Check endpoint URL, CORS, and server health.");
  } finally {
    clearTimeout(timeoutId);
  }

  let parsed;
  try {
    parsed = await response.json();
  } catch {
    throw new Error(`API returned non-JSON content (status ${response.status}).`);
  }

  if (!response.ok) {
    const detail = typeof parsed === "object" ? JSON.stringify(parsed) : String(parsed);
    throw new Error(`API request failed (${response.status}): ${detail}`);
  }

  if (typeof parsed?.session_id === "string" && parsed.session_id.trim()) {
    currentSessionId = parsed.session_id;
    updateSessionStatus();
  }

  if (typeof parsed?.user_id === "string" && parsed.user_id.trim()) {
    currentUserId = parsed.user_id;
    updateSessionStatus();
  }

  if (!parsed || typeof parsed !== "object" || typeof parsed.answer !== "string") {
    throw new Error("API response format is invalid. Expected JSON with an 'answer' string.");
  }

  return parsed;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  ensureSessionIdentity();

  const question = questionInput.value.trim();
  if (!question) {
    return;
  }

  const payload = {
    question,
    user_id: currentUserId,
    session_id: currentSessionId // Ensure the current session ID is sent with the payload
  };
  appendMessage("user", question);
  questionInput.value = "";
  setLoading(true);
  updateDebugPanels(payload, {});

  try {
    const data = await fetchAnswer(payload);
    const answerText = typeof data.answer === "string" ? data.answer : "No answer field returned.";
    const sources = Array.isArray(data.sources) ? data.sources : [];

    // The session ID is now updated inside fetchAnswer, so it will be ready for the next message.
    appendMessage("assistant", answerText, sources);
    updateDebugPanels(payload, data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error occurred.";
    appendMessage("error", message);
    updateDebugPanels(payload, { error: message });
  } finally {
    setLoading(false);
  }
});

clearBtn.addEventListener("click", () => {
  chatLog.innerHTML = "";
  updateSessionStatus();
  updateDebugPanels({}, {});
});

appendMessage(
  "assistant",
  "Ready. Send a question to test your API. This app waits up to 90 seconds for slower responses."
);
