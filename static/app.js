const cmdInput = document.getElementById("cmd");
const outputDiv = document.getElementById("output");

function appendOutput(text) {
  const pre = document.createElement("pre");
  pre.textContent = text;
  outputDiv.appendChild(pre);
  outputDiv.scrollTop = outputDiv.scrollHeight;
}

async function sendCommand(command) {
  appendOutput("> " + command);
  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });
    const data = await res.json();
    if (data.report) {
      appendOutput(data.report);
    } else if (data.error) {
      appendOutput("Error: " + data.error);
    } else {
      appendOutput("Unexpected response.");
    }
  } catch (err) {
    appendOutput("Network error: " + err.message);
  }
}

cmdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const command = cmdInput.value.trim();
    if (command) {
      sendCommand(command);
    }
    cmdInput.value = "";
  }
});