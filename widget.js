(function () {
  if (window.__MQW_LOADED__) {
    return;
  }
  window.__MQW_LOADED__ = true;

  var config = window.MedQuestWidgetConfig || {};
  var proxyPath = config.proxyPath || "/widget-api/chat";
  var position = config.position === "right" ? "right" : "left";
  var userId = generateId();
  var sessionId = generateId();

  function generateId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0,
        v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getSession() {
    console.log("MedQuest Widget Session Initialized:", {
      userId: userId,
      sessionId: sessionId
    });
  }

  function loadStyles() {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = config.stylesheetUrl || "/widget.css";
    document.head.appendChild(link);
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function formatInline(md) {
    return md
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>");
  }

  function markdownToHtml(input) {
    var safe = escapeHtml(input || "");
    var lines = safe.split(/\r?\n/);
    var out = [];
    var inList = false;

    for (var i = 0; i < lines.length; i += 1) {
      var line = lines[i].trim();

      if (!line) {
        if (inList) {
          out.push("</ul>");
          inList = false;
        }
        continue;
      }

      if (/^###\s+/.test(line)) {
        if (inList) {
          out.push("</ul>");
          inList = false;
        }
        out.push("<h3>" + formatInline(line.replace(/^###\s+/, "")) + "</h3>");
        continue;
      }

      if (/^##\s+/.test(line)) {
        if (inList) {
          out.push("</ul>");
          inList = false;
        }
        out.push("<h2>" + formatInline(line.replace(/^##\s+/, "")) + "</h2>");
        continue;
      }

      if (/^#\s+/.test(line)) {
        if (inList) {
          out.push("</ul>");
          inList = false;
        }
        out.push("<h1>" + formatInline(line.replace(/^#\s+/, "")) + "</h1>");
        continue;
      }

      if (/^[-*]\s+/.test(line)) {
        if (!inList) {
          out.push("<ul>");
          inList = true;
        }
        out.push("<li>" + formatInline(line.replace(/^[-*]\s+/, "")) + "</li>");
        continue;
      }

      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push("<p>" + formatInline(line) + "</p>");
    }

    if (inList) {
      out.push("</ul>");
    }

    return out.join("");
  }

  function addMessage(log, role, text, sources) {
    var el = document.createElement("div");
    el.className = "mqw-msg " + role;

    if (role === "assistant") {
      el.innerHTML = markdownToHtml(text);
    } else {
      el.textContent = text;
    }

    if (Array.isArray(sources) && sources.length > 0) {
      var sourceWrap = document.createElement("div");
      sourceWrap.className = "mqw-sources";

      var title = document.createElement("strong");
      title.textContent = "Sources";
      sourceWrap.appendChild(title);

      var list = document.createElement("ul");
      for (var i = 0; i < sources.length; i += 1) {
        var item = document.createElement("li");
        item.textContent = String(sources[i]);
        list.appendChild(item);
      }

      sourceWrap.appendChild(list);
      el.appendChild(sourceWrap);
    }

    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function addTypingIndicator(log) {
    var el = document.createElement("div");
    el.className = "mqw-msg assistant mqw-typing-msg";
    el.innerHTML = '<div class="mqw-typing"><span></span><span></span><span></span></div>';
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function buildUi() {
    var launcher = document.createElement("button");
    launcher.id = "mqw-launcher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", "Open chat assistant");
    launcher.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="28px" height="28px"><path d="M21 11.5C21 16.7467 16.7467 21 11.5 21C10.9893 21 10.4842 20.963 9.98699 20.8901L5.21052 22.9474C4.77842 23.1334 4.29915 22.8585 4.21052 22.4105C4.15236 22.1133 4.21052 21.8162 4.38421 21.5921L6.10253 19.5526C3.63684 17.5961 2 14.7105 2 11.5C2 6.25329 6.25329 2 11.5 2C16.7467 2 21 6.25329 21 11.5ZM8.5 10.5C7.67157 10.5 7 11.1716 7 12C7 12.8284 7.67157 13.5 8.5 13.5C9.32843 13.5 10 12.8284 10 12C10 11.1716 9.32843 10.5 8.5 10.5ZM14.5 10.5C13.6716 10.5 13 11.1716 13 12C13 12.8284 13.6716 13.5 14.5 13.5C15.3284 13.5 16 12.8284 16 12C16 11.1716 15.3284 10.5 14.5 10.5Z"/></svg>';

    var panel = document.createElement("section");
    panel.id = "mqw-panel";
    panel.setAttribute("data-open", "false");

    if (position === "right") {
      launcher.style.left = "auto";
      launcher.style.right = "18px";
      panel.style.left = "auto";
      panel.style.right = "18px";
    }

    panel.innerHTML = ""
      + '<div class="mqw-header">'
      + "<h3>Med-QUEST Assistant</h3>"
      + '<a class="mqw-preassess" href="https://dksph266ybqbw.cloudfront.net" target="_blank" rel="noopener noreferrer">Pre-assessment</a>'
      + '<button class="mqw-close" type="button" aria-label="Close chat">x</button>'
      + "</div>"
      + '<div class="mqw-log" id="mqw-log"></div>'
      + '<form class="mqw-form" id="mqw-form">'
      + '<textarea id="mqw-question" placeholder="Ask a question..." required></textarea>'
      + '<div class="mqw-row">'
      + '<span class="mqw-status" id="mqw-status">Ready</span>'
      + '<button class="mqw-send" id="mqw-send" type="submit">Send</button>'
      + "</div>"
      + "</form>";

    document.body.appendChild(launcher);
    document.body.appendChild(panel);

    var closeBtn = panel.querySelector(".mqw-close");
    var log = panel.querySelector("#mqw-log");
    var form = panel.querySelector("#mqw-form");
    var input = panel.querySelector("#mqw-question");
    var sendBtn = panel.querySelector("#mqw-send");
    var status = panel.querySelector("#mqw-status");

    function openPanel() {
      panel.setAttribute("data-open", "true");
      input.focus();
    }

    function closePanel() {
      panel.setAttribute("data-open", "false");
    }

    launcher.addEventListener("click", function () {
      if (panel.getAttribute("data-open") === "true") {
        closePanel();
      } else {
        openPanel();
      }
    });

    closeBtn.addEventListener("click", closePanel);

    addMessage(
      log,
      "assistant",
      "### Aloha\nI can help answer Med-QUEST questions. Ask me anything about coverage, forms, or services.",
      []
    );

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      var question = input.value.trim();
      if (!question) {
        return;
      }

      addMessage(log, "user", question, []);
      input.value = "";
      sendBtn.disabled = true;
      status.textContent = "Waiting for response...";
      var typingEl = addTypingIndicator(log);

      const payload = {
        question: question,
        user_id: userId,
        session_id: sessionId
      };

      console.log("Sending payload:", payload);

      try {
        var response = await fetch(proxyPath, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        var data;
        try {
          data = await response.json();
        } catch (_err) {
          throw new Error("Widget received non-JSON response.");
        }

        if (!response.ok) {
          throw new Error(data.answer || "API request failed.");
        }

        typingEl.remove();
        addMessage(log, "assistant", data.answer || "No answer returned.", data.sources || []);
        status.textContent = "Ready";
      } catch (err) {
        typingEl.remove();
        var message = err && err.message ? err.message : "API is not working right now.";
        addMessage(log, "error", message, []);
        status.textContent = "Error";
      } finally {
        sendBtn.disabled = false;
      }
    });
  }

  loadStyles();
  getSession();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildUi);
  } else {
    buildUi();
  }
})();
