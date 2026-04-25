const statusLine = document.querySelector("#status");

if (statusLine) {
  const time = new Date().toLocaleTimeString();
  statusLine.textContent = `Page ready at ${time}.`;
}
