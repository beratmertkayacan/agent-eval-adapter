let current = null;

function element(id) {
  return document.getElementById(id);
}

function setText(id, text) {
  element(id).textContent = text ?? "-";
}

function showError(message) {
  element("error").textContent = message;
}

async function callApi(method, path, body) {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

// A JSON object is sent as an object. Anything else is sent as text.
function readInput() {
  const text = element("input").value;
  try {
    const value = JSON.parse(text);
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      return value;
    }
  } catch (error) {
    // Not JSON, so it is plain text.
  }
  return text;
}

function updateContinueBox() {
  const sameAgent = current !== null && current.agentId === element("agent").value;
  element("continue").disabled = !sameAgent;
  if (!sameAgent) {
    element("continue").checked = false;
  }
  setText("continue-run", current ? current.runId : "the last run");
}

function showRun(run) {
  current = run;
  const normalized = run.normalizedResponse;
  element("result").hidden = false;
  setText("run-id", run.runId);
  setText("run-agent", run.agentId);
  setText("status", normalized.response.status);
  setText("session-id", run.sessionId);
  setText("turn", run.turn);
  setText("latency", `${run.latencyMs} ms`);
  setText("http-status", run.httpStatus);
  setText("replay-of", run.replayOf);
  setText("run-error", run.error ? `${run.error.type}: ${run.error.message}` : "none");
  setText("normalized", JSON.stringify(normalized, null, 2));
  setText("raw", JSON.stringify(run.rawResponse, null, 2));
  updateContinueBox();
}

function addHistoryRow(run) {
  const row = element("history").insertRow();
  const cells = [
    run.replayOf ? `${run.runId} (replay of ${run.replayOf})` : run.runId,
    run.agentId,
    run.normalizedResponse.response.status,
    run.sessionId,
    run.turn,
    `${run.latencyMs} ms`,
    run.error ? run.error.type : "none",
  ];
  for (const value of cells) {
    row.insertCell().textContent = value ?? "-";
  }
  const button = document.createElement("button");
  button.textContent = "View";
  button.addEventListener("click", () => showRun(run));
  row.insertCell().append(button);
}

async function loadHistory() {
  const runs = await callApi("GET", "/runs");
  element("history").replaceChildren();
  for (const run of runs.reverse()) {
    addHistoryRow(run);
  }
}

async function loadAgents() {
  const agents = await callApi("GET", "/agents");
  for (const agentId of agents) {
    const option = document.createElement("option");
    option.textContent = agentId;
    element("agent").append(option);
  }
  if (agents.includes("warehouse-agent")) {
    element("agent").value = "warehouse-agent";
  }
}

// Runs one action, shows the new run and refreshes the history.
async function run(buttonId, action) {
  showError("");
  element(buttonId).disabled = true;
  try {
    showRun(await action());
    await loadHistory();
  } catch (error) {
    showError(error.message);
  } finally {
    element(buttonId).disabled = false;
  }
}

function send() {
  const body = { input: readInput() };
  if (element("continue").checked && current) {
    body.previousRunId = current.runId;
  }
  return run("send", () => callApi("POST", `/agents/${element("agent").value}/invoke`, body));
}

function replay() {
  return run("replay", () => callApi("POST", `/runs/${current.runId}/replay`));
}

element("send").addEventListener("click", send);
element("replay").addEventListener("click", replay);
element("agent").addEventListener("change", updateContinueBox);

loadAgents().then(loadHistory).catch((error) => showError(error.message));
