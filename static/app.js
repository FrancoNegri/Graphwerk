/* graphwerk review UI: Cytoscape graph + review sidebar.
 * Polls /api/hash; refetches the graph whenever either tree changes. */

const COLORS = {
  modified: "#ef4444",
  added: "#3b82f6",
  deleted: "#64748b",
  affected: "#f59e0b",
  unchanged: "#475569",
};

let cy = null;
let currentHash = null;
let nodesById = {};
let selectedId = null;

async function loadGraph() {
  const res = await fetch("/api/graph");
  const data = await res.json();
  currentHash = data.hash;
  nodesById = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  document.getElementById("paths").innerHTML =
    `agent workspace: ${esc(data.staged)}<br>your tree: ${esc(data.base)}`;

  const elements = toElements(data);
  if (cy && sameTopology(elements)) {
    for (const n of data.nodes) cy.getElementById(n.id).data("status", n.status);
  } else {
    renderGraph(elements);
  }
  if (selectedId) {
    if (nodesById[selectedId]) showDetails(nodesById[selectedId]);
    else clearDetails();
  }
}

function toElements(data) {
  const nodes = data.nodes.map((n) => ({
    data: { id: n.id, label: n.label, kind: n.kind, status: n.status, parent: n.parent || undefined },
  }));
  const ids = new Set(data.nodes.map((n) => n.id));
  const edges = data.edges
    .filter((e) => ids.has(e.source) && ids.has(e.target))
    .map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target, kind: e.kind } }));
  return { nodes, edges };
}

function sameTopology(elements) {
  const ids = new Set(elements.nodes.map((n) => n.data.id));
  const current = cy.nodes().map((n) => n.id());
  return current.length === ids.size && current.every((id) => ids.has(id));
}

function renderGraph(elements) {
  if (cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    wheelSensitivity: 0.3,
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          color: "#e2e8f0",
          "font-size": 11,
          "text-valign": "center",
          "background-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
          "border-width": 1.5,
          "border-color": "#0f172a",
          width: "label",
          height: 12,
          shape: "round-rectangle",
          padding: "7px",
        },
      },
      {
        selector: "node[kind='class']",
        style: {
          shape: "round-rectangle",
          "text-valign": "top",
          "text-margin-y": -4,
          "background-opacity": 0.25,
          "border-width": 2,
          "border-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
          padding: "10px",
        },
      },
      {
        selector: "node[kind='file']",
        style: {
          shape: "round-rectangle",
          "text-valign": "top",
          "text-margin-y": -6,
          "font-size": 12,
          "background-color": "#1e293b",
          "background-opacity": 0.6,
          "border-width": 2,
          "border-color": (ele) => COLORS[ele.data("status")] || "#334155",
          padding: "14px",
        },
      },
      {
        selector: "node[status='deleted']",
        style: { "border-style": "dashed", opacity: 0.6 },
      },
      {
        selector: "edge",
        style: {
          width: 1.5,
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.8,
          "line-color": "#475569",
          "target-arrow-color": "#475569",
        },
      },
      {
        selector: "edge[kind='imports']",
        style: { "line-style": "dashed", "line-color": "#334155", "target-arrow-color": "#334155" },
      },
      { selector: "node:selected", style: { "border-color": "#f8fafc", "border-width": 3 } },
    ],
    layout: layoutOptions(),
  });
  cy.on("tap", "node", (evt) => {
    selectedId = evt.target.id();
    showDetails(nodesById[selectedId]);
  });
  cy.on("tap", (evt) => {
    if (evt.target === cy) clearDetails();
  });
}

function layoutOptions() {
  // fcose packs compound (file/class) boxes tightly around their children,
  // so box size tracks content instead of layout scatter.
  return {
    name: "fcose",
    animate: false,
    quality: "proof",
    padding: 30,
    nodeSeparation: 75,
    idealEdgeLength: 70,
    nestingFactor: 0.1,
  };
}

function showDetails(node) {
  if (!node) return;
  document.getElementById("placeholder").hidden = true;
  const details = document.getElementById("details");
  details.hidden = false;

  document.getElementById("d-label").textContent = node.label;
  document.getElementById("d-kind").textContent = node.kind;
  const statusChip = document.getElementById("d-status");
  statusChip.textContent = node.status;
  statusChip.className = `chip ${node.status}`;
  document.getElementById("d-path").textContent = node.path;

  const whySection = document.getElementById("why-section");
  whySection.hidden = !node.why;
  if (node.why) document.getElementById("d-why").textContent = node.why;

  const diffSection = document.getElementById("diff-section");
  diffSection.hidden = !node.diff;
  if (node.diff) document.getElementById("d-diff").innerHTML = renderDiff(node.diff);

  const changed = ["modified", "added", "deleted"].includes(node.status);
  const applyBtn = document.getElementById("btn-apply");
  applyBtn.hidden = !changed;
  applyBtn.textContent = `Apply file ${node.path}`;
  applyBtn.onclick = () => applyFile(node.path);

  document.getElementById("reject-box").hidden = !changed;
  document.getElementById("reject-result").hidden = true;
  document.getElementById("btn-reject").onclick = () => rejectNode(node);
}

function clearDetails() {
  selectedId = null;
  document.getElementById("placeholder").hidden = false;
  document.getElementById("details").hidden = true;
}

async function applyFile(path) {
  const res = await fetch("/api/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  const data = await res.json();
  toast(res.ok ? `✓ ${data.result}` : `error: ${data.detail}`);
  if (res.ok) loadGraph();
}

async function rejectNode(node) {
  const comment = document.getElementById("reject-comment").value.trim();
  if (!comment) return toast("write a comment first — it becomes the re-prompt");
  const res = await fetch("/api/reject", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: node.id,
      label: node.label,
      status: node.status,
      diff: node.diff || "",
      comment,
    }),
  });
  const data = await res.json();
  if (res.ok) {
    document.getElementById("reject-result").hidden = false;
    document.getElementById("reject-prompt").textContent = data.prompt;
    document.getElementById("reject-comment").value = "";
  } else {
    toast(`error: ${data.detail}`);
  }
}

function renderDiff(diff) {
  return diff
    .split("\n")
    .map((line) => {
      const cls = line.startsWith("+") ? "add" : line.startsWith("-") ? "del"
        : line.startsWith("@@") ? "hunk" : "ctx";
      return `<span class="${cls}">${esc(line)}</span>`;
    })
    .join("\n");
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

let toastTimer = null;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3000);
}

setInterval(async () => {
  try {
    const res = await fetch("/api/hash");
    const data = await res.json();
    if (data.hash !== currentHash) loadGraph();
  } catch {
    /* server briefly unreachable; keep polling */
  }
}, 1500);

loadGraph();
