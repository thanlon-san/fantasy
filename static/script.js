// API Base URL
const API_BASE = window.location.origin;

// State
let currentRecap = null;
let currentWeek = null;

// DOM Elements
const weekInput = document.getElementById("weekInput");
const personaSelect = document.getElementById("personaSelect");
const formatSelect = document.getElementById("formatSelect");
const modelSelect = document.getElementById("modelSelect");
const generateBtn = document.getElementById("generateBtn");
const generateStatus = document.getElementById("generateStatus");
const recapDisplay = document.getElementById("recapDisplay");
const recapWeek = document.getElementById("recapWeek");
const recapContent = document.getElementById("recapContent");
const historyList = document.getElementById("historyList");
const toast = document.getElementById("toast");

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    await loadLeagueInfo();
    await loadHistory();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
  generateBtn.addEventListener("click", generateRecap);
  document
    .getElementById("copySlackBtn")
    .addEventListener("click", copyForSlack);

  weekInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
            generateRecap();
        }
    });
}

// Load league info to get current week
async function loadLeagueInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/league`);
        if (response.ok) {
            const data = await response.json();
            // ESPN's current_week is the upcoming week, so subtract 1 for the most recent completed week
            const completedWeek = Math.max(1, (data.current_week || 1) - 1);
            weekInput.value = completedWeek;
        }
    } catch (error) {
    console.error("Failed to load league info:", error);
    }
}

// Load recap history
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/recaps/history`);
        if (!response.ok) {
      throw new Error("Failed to load history");
        }
        
        const data = await response.json();
        displayHistory(data.recaps || []);
    } catch (error) {
    console.error("Failed to load history:", error);
    historyList.innerHTML =
      '<p class="no-history">No recaps generated yet. Create your first one above!</p>';
    }
}

// Display history
function displayHistory(recaps) {
    if (recaps.length === 0) {
    historyList.innerHTML =
      '<p class="no-history">No recaps generated yet. Create your first one above!</p>';
        return;
    }

    // Sort by week descending
    recaps.sort((a, b) => b.week - a.week);

  historyList.innerHTML = recaps
    .map((recap) => {
        const date = new Date(recap.date);
      const formattedDate = date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        });

        // Extract first line as headline
      const headline = recap.recap
        .split("\n")[0]
        .replace(/^#+ /, "")
        .substring(0, 60);

        return `
            <div class="history-item" onclick="loadRecap(${recap.week})">
                <div class="history-item-info">
                    <div class="history-item-week">Week ${recap.week}</div>
                    <div class="history-item-date">${formattedDate}</div>
                    <div class="history-item-headline">${headline}...</div>
                </div>
                <div class="history-item-action">View →</div>
            </div>
        `;
    })
    .join("");
}

// Load a specific recap
async function loadRecap(week) {
    try {
        const response = await fetch(`${API_BASE}/api/recaps/${week}`);
        if (!response.ok) {
            throw new Error(`Recap for week ${week} not found`);
        }

        const data = await response.json();
        displayRecap(week, data.recap);
    showToast(`Loaded Week ${week} recap`, "success");
        
        // Scroll to recap
    recapDisplay.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
    console.error("Failed to load recap:", error);
    showToast(`Failed to load Week ${week} recap`, "error");
    }
}

// Generate new recap
async function generateRecap() {
    const week = parseInt(weekInput.value);
  const persona = personaSelect.value;
  const format = formatSelect ? formatSelect.value : "v3";
  const model = modelSelect ? modelSelect.value : "auto";
    
    if (!week || week < 1 || week > 18) {
    showStatus("Please enter a valid week number (1-18)", "error");
        return;
    }

    // Disable button and show loading
    setGenerating(true);
  const personaLabel = persona ? persona.replace(" Ghost", "") : "Random persona";
  const formatLabel = format === "v3" ? "V3 Lean" : "V2 Structured";
  const modelLabel = model === "anthropic" ? "Claude" : model === "openai" ? "GPT-4o" : "Auto";
  showStatus(
    `Generating recap with ${personaLabel} (${formatLabel}, ${modelLabel})... This may take 30-60 seconds ⏳`,
    "loading"
  );

    try {
        const requestBody = { 
            week: week,
            use_v3_format: format === "v3",
            use_v2_format: format === "v2",
            model_provider: model,
        };
        if (persona) {
            requestBody.persona = persona;
        }
        
        const response = await fetch(`${API_BASE}/api/recaps/generate`, {
      method: "POST",
            headers: {
        "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const error = await response.json();
      throw new Error(error.detail || "Failed to generate recap");
        }

        const data = await response.json();
        
        // Display the recap
        displayRecap(week, data.recap);
    const successPersona = persona ? persona.replace(" Ghost", "") : "random persona";
    const successFormat = format === "v3" ? "V3 Lean" : "V2";
    const successModel = data.model || modelLabel;
    showStatus(`✅ Recap generated successfully with ${successPersona} (${successFormat}, ${successModel})!`, "success");
    showToast("Recap generated successfully!", "success");
        
        // Reload history
        await loadHistory();
        
        // Scroll to recap
        setTimeout(() => {
      recapDisplay.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
    } catch (error) {
    console.error("Generation error:", error);
    showStatus(`❌ Error: ${error.message}`, "error");
    showToast(`Failed to generate recap: ${error.message}`, "error");
    } finally {
        setGenerating(false);
    }
}

// Display recap (show Slack format in preview)
function displayRecap(week, content) {
  currentRecap = content;
  currentWeek = week;

  recapWeek.textContent = `Week ${week}`;

  // Display the Slack-formatted text directly (plain text with zero-width spaces)
  const slackText = convertToSlackFormat(content);
  recapContent.textContent = slackText;

  recapDisplay.style.display = "block";
}

// Convert markdown to Slack format - completely rewritten
function convertToSlackFormat(markdown) {
  const lines = markdown.split("\n");
  const output = [];

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Preserve empty lines for Slack spacing
    if (!line.trim()) {
      output.push("");
      continue;
    }

    // Section headers with bold emoji (e.g., **:football: Week 11**)
    // Keep the line as-is for Slack markdown
    if (line.startsWith("**:") && line.includes("**")) {
      output.push(line);
      continue;
    }

    // Main heading (H1)
    if (line.startsWith("# ")) {
      output.push("");
      output.push("*" + line.substring(2) + "* 🏈");
      output.push("");
      continue;
    }

    // Matchup headlines with bold (e.g., **@Owner's Team Wins**)
    // Keep the line as-is for Slack markdown
    if (line.startsWith("**") && line.includes("@") && line.endsWith("**")) {
      output.push(line);
      continue;
    }

    // Legacy: Matchup headers (H3 with @Owner) - for backwards compatibility
    if (line.startsWith("### ") && line.includes("@")) {
      output.push("");
      // Strip ### and convert **bold** to *bold* - do NOT use regex on individual chars
      line = line.substring(4); // Remove ###
      // Simple string replace for bold markers
      while (line.includes("**")) {
        line = line.replace("**", "*");
      }
      output.push(line);
      continue;
    }

    // Section headers (H2/H3)
    if (line.startsWith("## ") || line.startsWith("### ")) {
      output.push("");
      line = line.replace(/^#+\s+/, "");
      // Remove emoji markup and bold markers
      while (line.includes("**")) {
        line = line.replace("**", "");
      }
      output.push("*" + line + "*");
      output.push("");
      continue;
    }

    // Blockquotes - keep them and add space after
    if (line.startsWith("> ")) {
      output.push(line);
      output.push("");
      continue;
    }

    // Skip dividers entirely
    if (/^---+$/.test(line)) {
      continue;
    }

    // Taglines - add space after
    if (line.includes("Tagline:")) {
      // Simple replace
      line = line.replace("**Tagline:**", "Tagline:");
      line = line.replace("*Tagline:*", "Tagline:");
      output.push(line);
      output.push("");
      continue;
    }

    // Lists - add bullet
    if (line.match(/^[-*]\s+/)) {
      output.push("  • " + line.replace(/^[-*]\s+/, ""));
      continue;
    }

    // Keep markdown bold as-is (**text**) - Slack supports this
    // No conversion needed
    
    // Regular line
    output.push(line);
  }

  // Join with newlines - preserve blank lines as-is
  let result = output.join("\n");
  return result.trim();
}

// Render a trimmed HTML preview and for rich clipboard copy
function renderMarkdownToHtml(markdown) {
  const lines = markdown.split(/\n/);
  let htmlParts = [];
  let inList = false;
  let withinMatchups = false;

  const flushList = () => {
    if (inList) {
      htmlParts.push("</ul>");
      inList = false;
    }
  };

  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const fmtInline = (s) => {
    // Bold then italics
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|\s)\*(?!\s)([^*]+?)\*(?=\s|$)/g, "$1<em>$2</em>");
    return s;
  };

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trimEnd();
    if (line.trim() === "") {
      flushList();
      continue;
    }

    // Section state
    if (/^##\s+Matchups/.test(line)) {
      withinMatchups = true;
    }
    if (
      /^##\s+🏆|^##\s+\*🏆/.test(line) ||
      /^##\s+🏈|^##\s+\*🏈/.test(line) ||
      /^##\s+🧘/.test(line)
    ) {
      withinMatchups = false;
    }

    // Horizontal rule (skip inside matchups)
    if (/^---+$/.test(line)) {
      flushList();
      if (!withinMatchups) htmlParts.push("<hr>");
      continue;
    }

    // Headings
    let m;
    if ((m = line.match(/^#\s+(.+)$/))) {
      flushList();
      htmlParts.push(`<h1>${fmtInline(esc(m[1]))}</h1>`);
      continue;
    }
    if ((m = line.match(/^##\s+(.+)$/))) {
      flushList();
      htmlParts.push(`<h2>${fmtInline(esc(m[1]))}</h2>`);
      continue;
    }
    if ((m = line.match(/^###\s+(.+)$/))) {
      flushList();
      htmlParts.push(`<h3>${fmtInline(esc(m[1]))}</h3>`);
      continue;
    }

    // Blockquote
    if ((m = line.match(/^>\s+(.+)$/))) {
      flushList();
      htmlParts.push(`<blockquote>${fmtInline(esc(m[1]))}</blockquote>`);
      continue;
    }

    // Bulleted list
    if (/^[-•]\s+/.test(line)) {
      if (!inList) {
        htmlParts.push("<ul>");
        inList = true;
      }
      htmlParts.push(
        `<li>${fmtInline(esc(line.replace(/^[-•]\s+/, "")))}</li>`
      );
      continue;
    }

    // Tagline emphasis
    if ((m = line.match(/^\*Tagline:\*\s*(.+)$/))) {
      flushList();
      htmlParts.push(`<p><em>Tagline:</em> ${fmtInline(esc(m[1]))}</p>`);
      continue;
    }

    // Default paragraph
    flushList();
    htmlParts.push(`<p>${fmtInline(esc(line))}</p>`);
  }

  flushList();
  return htmlParts.join("\n");
}

// Render a simplified RTF variant to improve rich paste preservation in Slack
function renderRtfFromMarkdown(markdown) {
  const esc = (s) =>
    s.replace(/\\/g, "\\\\").replace(/{/g, "\\{").replace(/}/g, "\\}");

  const lines = markdown.split(/\n/);
  let out = ["{\\rtf1\\ansi\\deff0"];

  const pushPar = (txt) => out.push(esc(txt) + "\\par ");

  for (let raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      out.push("\\par ");
      continue;
    }
    let m;
    if ((m = line.match(/^#\s+(.+)$/))) {
      out.push("\\b " + esc(m[1]) + " \\b0\\par ");
      continue;
    }
    if ((m = line.match(/^##\s+(.+)$/))) {
      out.push("\\b " + esc(m[1]) + " \\b0\\par ");
      continue;
    }
    if ((m = line.match(/^###\s+(.+)$/))) {
      out.push("\\b " + esc(m[1]) + " \\b0\\par ");
      continue;
    }
    if ((m = line.match(/^>\s+(.+)$/))) {
      out.push("\\i " + esc(m[1]) + " \\i0\\par ");
      continue;
    }
    if (/^---+$/.test(line)) {
      out.push("\\par ");
      continue;
    }
    if (/^[-•]\s+/.test(line)) {
      out.push(esc("• " + line.replace(/^[-•]\s+/, "")) + "\\par ");
      continue;
    }
    if ((m = line.match(/^\*Tagline:\*\s*(.+)$/))) {
      out.push("\\i " + esc("Tagline: " + m[1]) + " \\i0\\par ");
      continue;
    }
    // Bold inline **...**
    let txt = line.replace(
      /\*\*(.+?)\*\*/g,
      (__, g1) => "\\b " + esc(g1) + " \\b0"
    );
    pushPar(txt);
  }

  out.push("}");
  return out.join("");
}

// Copy to clipboard (Slack format - this is the only copy function now)
async function copyForSlack() {
    if (!currentRecap) return;

  // Prepare HTML (rich) and plain text (Slack-friendly) variants
  const html = renderMarkdownToHtml(currentRecap);
  const plain = convertToSlackFormat(currentRecap);
  const rtf = renderRtfFromMarkdown(currentRecap);

  // Try modern ClipboardItem with text/html for rich paste into Slack
  try {
    if (window.ClipboardItem) {
      const item = new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/rtf": new Blob([rtf], { type: "text/rtf" }),
        "text/plain": new Blob([plain], { type: "text/plain" }),
      });
      await navigator.clipboard.write([item]);
      showToast("✅ Copied formatted recap (rich paste)", "success");
      return;
    }
        } catch (err) {
    console.warn("ClipboardItem failed, falling back:", err);
  }

  // Fallback: copy using a contenteditable container to preserve formatting
  try {
    const div = document.createElement("div");
    div.contentEditable = "true";
    div.style.position = "fixed";
    div.style.left = "-999999px";
    div.innerHTML = html;
    document.body.appendChild(div);

    const range = document.createRange();
    range.selectNodeContents(div);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    const ok = document.execCommand("copy");
    sel.removeAllRanges();
    document.body.removeChild(div);
    if (ok) {
      showToast("✅ Copied formatted recap (rich paste)", "success");
      return;
    }
  } catch (err) {
    console.warn("Rich copy fallback failed, falling back to plain:", err);
  }

  // Final fallback: plain text
  try {
    await navigator.clipboard.writeText(plain);
    showToast("✅ Copied to clipboard - ready for Slack!", "success");
  } catch (error) {
    console.error("Failed to copy:", error);
    showToast("❌ Failed to copy to clipboard", "error");
    }
}

// Download recap as markdown file (original format)
function downloadRecap() {
    if (!currentRecap || !currentWeek) return;

    // Download the original markdown version
  const blob = new Blob([currentRecap], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
    a.href = url;
    a.download = `week-${currentWeek}-recap.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
  showToast(`💾 Downloaded week-${currentWeek}-recap.md`, "success");
}

// UI Helper Functions
function setGenerating(isGenerating) {
    generateBtn.disabled = isGenerating;
  const btnText = generateBtn.querySelector(".btn-text");
  const spinner = generateBtn.querySelector(".spinner");
    
    if (isGenerating) {
    btnText.textContent = "Generating...";
    spinner.style.display = "inline-block";
    } else {
    btnText.textContent = "Generate Recap";
    spinner.style.display = "none";
    }
}

function showStatus(message, type) {
    generateStatus.textContent = message;
    generateStatus.className = `status-message ${type} show`;
    
  if (type === "success" || type === "error") {
        setTimeout(() => {
      generateStatus.classList.remove("show");
        }, 5000);
    }
}

function showToast(message, type = "") {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
    toast.classList.remove("show");
    }, 3000);
}

// Make functions available globally
window.loadRecap = loadRecap;
window.copyForSlack = copyForSlack;
