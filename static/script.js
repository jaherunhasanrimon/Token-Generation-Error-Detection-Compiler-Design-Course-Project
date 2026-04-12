const codeInput = document.getElementById("codeInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const copyBtn = document.getElementById("copyBtn");
const downloadBtn = document.getElementById("downloadBtn");
const tokenBody = document.getElementById("tokenBody");
const errorBody = document.getElementById("errorBody");
const totalTokens = document.getElementById("totalTokens");
const totalErrors = document.getElementById("totalErrors");
const lexerStatus = document.getElementById("lexerStatus");
const heroStatus = document.getElementById("heroStatus");
const liveTokenCount = document.getElementById("liveTokenCount");
const liveErrorCount = document.getElementById("liveErrorCount");
const statusMessage = document.getElementById("statusMessage");
const loader = document.getElementById("loader");
const lineNumbers = document.getElementById("lineNumbers");

let latestResult = {
  tokens: [],
  errors: [],
  summary: { total_tokens: 0, total_errors: 0 },
  raw_output: "",
};

function setStatus(message, state = "") {
  statusMessage.textContent = message;
  statusMessage.className = "status-message";

  if (state) {
    statusMessage.classList.add(`is-${state}`);
  }
}

function setBusy(isBusy) {
  analyzeBtn.disabled = isBusy;
  copyBtn.disabled = isBusy;
  downloadBtn.disabled = isBusy;
  loader.classList.toggle("hidden", !isBusy);
  lexerStatus.textContent = isBusy ? "Analyzing" : lexerStatus.textContent;
  heroStatus.textContent = isBusy ? "Running" : heroStatus.textContent;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function tokenRowClass(type) {
  return `row-${type.toLowerCase()}`;
}

function renderEmptyState(target, text, columns) {
  target.innerHTML = `<tr class="empty-row"><td colspan="${columns}">${text}</td></tr>`;
}

function updateLineNumbers() {
  const lineCount = codeInput.value.split("\n").length || 1;
  lineNumbers.textContent = Array.from({ length: lineCount }, (_, index) => index + 1).join("\n");
}

function renderTokens(tokens) {
  if (!tokens.length) {
    renderEmptyState(tokenBody, "No tokens were produced.", 3);
    return;
  }

  tokenBody.innerHTML = tokens
    .map(
      (token, index) => `
        <tr class="${tokenRowClass(token.type)}" style="animation-delay:${index * 30}ms">
          <td>${token.line}</td>
          <td>${escapeHtml(token.type)}</td>
          <td><code>${escapeHtml(token.lexeme)}</code></td>
        </tr>
      `,
    )
    .join("");
}

function renderErrors(errors) {
  if (!errors.length) {
    renderEmptyState(errorBody, "No lexical errors detected.", 3);
    return;
  }

  errorBody.innerHTML = errors
    .map(
      (error, index) => `
        <tr class="row-error" style="animation-delay:${index * 40}ms">
          <td>${error.line}</td>
          <td><code>${escapeHtml(error.lexeme)}</code></td>
          <td>${escapeHtml(error.message)}</td>
        </tr>
      `,
    )
    .join("");
}

function updateSummary(summary) {
  totalTokens.textContent = summary.total_tokens;
  totalErrors.textContent = summary.total_errors;
  liveTokenCount.textContent = `${summary.total_tokens} tokens`;
  liveErrorCount.textContent = `${summary.total_errors} errors`;
}

function buildTextExport(result) {
  const tokenLines = result.tokens.map(
    (token) => `${token.line} | ${token.type} | ${token.lexeme}`,
  );
  const errorLines = result.errors.map(
    (error) => `ERROR | ${error.line} | ${error.lexeme} | ${error.message}`,
  );

  return [
    "TOKEN TAGGER ANALYSIS",
    "",
    "TOKENS",
    ...tokenLines,
    "",
    "ERRORS",
    ...(errorLines.length ? errorLines : ["None"]),
    "",
    `Total Tokens: ${result.summary.total_tokens}`,
    `Total Errors: ${result.summary.total_errors}`,
  ].join("\n");
}

async function analyzeCode() {
  const code = codeInput.value;

  if (!code.trim()) {
    setStatus("Please enter some source code to analyze.", "error");
    lexerStatus.textContent = "Waiting";
    heroStatus.textContent = "Waiting";
    return;
  }

  setBusy(true);
  setStatus("Running lexical analysis...");

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ code }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Analysis failed.");
    }

    latestResult = data;
    renderTokens(data.tokens);
    renderErrors(data.errors);
    updateSummary(data.summary);
    lexerStatus.textContent = data.summary.total_errors ? "Warnings Found" : "Clean";
    heroStatus.textContent = data.summary.total_errors ? "Review Needed" : "Ready";
    setStatus("Analysis complete.", "success");
  } catch (error) {
    latestResult = {
      tokens: [],
      errors: [],
      summary: { total_tokens: 0, total_errors: 0 },
      raw_output: "",
    };
    renderEmptyState(tokenBody, "No tokens were produced.", 3);
    renderEmptyState(errorBody, "No errors to display.", 3);
    updateSummary(latestResult.summary);
    lexerStatus.textContent = "Failed";
    heroStatus.textContent = "Attention";
    setStatus(error.message || "Unable to analyze the code.", "error");
  } finally {
    setBusy(false);
  }
}

async function copyOutput() {
  const text = buildTextExport(latestResult);

  try {
    await navigator.clipboard.writeText(text);
    setStatus("Token output copied to the clipboard.", "success");
  } catch {
    setStatus("Clipboard copy failed in this browser.", "error");
  }
}

function downloadOutput() {
  const blob = new Blob([buildTextExport(latestResult)], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "token-tagger-output.txt";
  link.click();

  URL.revokeObjectURL(url);
  setStatus("Analysis exported as token-tagger-output.txt.", "success");
}

analyzeBtn.addEventListener("click", analyzeCode);
copyBtn.addEventListener("click", copyOutput);
downloadBtn.addEventListener("click", downloadOutput);

codeInput.addEventListener("input", () => {
  const roughTokenCount = codeInput.value.trim()
    ? codeInput.value.trim().split(/\s+/).filter(Boolean).length
    : 0;
  liveTokenCount.textContent = `${roughTokenCount} words`;
  if (!codeInput.value.trim()) {
    liveErrorCount.textContent = "0 errors";
    heroStatus.textContent = "Ready";
  }
  updateLineNumbers();
});

codeInput.addEventListener("scroll", () => {
  lineNumbers.scrollTop = codeInput.scrollTop;
});

updateLineNumbers();
