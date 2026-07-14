/* graphwerk review UI: Cytoscape graph + review sidebar.
 * Polls /api/hash; refetches the graph whenever either tree changes. */

const COLORS = {
  modified: "#ef4444",
  added: "#3b82f6",
  deleted: "#64748b",
  affected: "#f59e0b",
  unchanged: "#475569",
};

const STATUS_RANK = ["modified", "added", "deleted", "affected", "unchanged"];

let cy = null;
let currentHash = null;
let graphData = null;
let nodesById = {};
let selectedId = null;
const collapsedFileIds = new Set();
let changedOnlyView = false;

async function loadGraph() {
  const res = await fetch("/api/graph");
  const data = await res.json();
  currentHash = data.hash;
  graphData = data;
  nodesById = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  for (const id of [...collapsedFileIds]) {
    if (!nodesById[id] || nodesById[id].kind !== "file") collapsedFileIds.delete(id);
  }
  document.getElementById("paths").innerHTML =
    `agent workspace: ${esc(data.staged)}<br>your tree: ${esc(data.base)}`;

  const elements = toElements(data);
  if (cy && sameTopology(elements)) {
    for (const n of elements.nodes) {
      const ele = cy.getElementById(n.data.id);
      ele.data("status", n.data.status);
      if (collapsedFileIds.has(n.data.id)) ele.data("collapsedStatus", n.data.collapsedStatus);
    }
  } else {
    renderGraph(elements);
  }
  if (selectedId) {
    if (nodesById[selectedId]) showDetails(nodesById[selectedId]);
    else clearDetails();
  }
}

function toElements(data) {
  const parentOf = new Map(data.nodes.map((n) => [n.id, n.parent]));

  // A node hidden inside a collapsed file is represented by that file node;
  // everything else represents itself.
  const representativeId = (id) => {
    let representative = id;
    for (let ancestor = parentOf.get(id); ancestor; ancestor = parentOf.get(ancestor)) {
      if (collapsedFileIds.has(ancestor)) representative = ancestor;
    }
    return representative;
  };

  const revealedIds = changedOnlyView ? changedAndBlastRadiusIds(data.nodes, parentOf) : null;

  const nodes = data.nodes
    .filter((n) => representativeId(n.id) === n.id && (!revealedIds || revealedIds.has(n.id)))
    .map((n) => {
      const nodeData = { id: n.id, label: n.label, kind: n.kind, status: n.status, parent: n.parent || undefined };
      if (collapsedFileIds.has(n.id)) {
        nodeData.collapsedStatus = strongestDescendantStatus(n.id, data.nodes, parentOf);
      }
      return { data: nodeData };
    });

  const renderedIds = new Set(nodes.map((n) => n.data.id));
  const seenEdgeIds = new Set();
  const edges = [];
  for (const e of data.edges) {
    const source = representativeId(e.source);
    const target = representativeId(e.target);
    if (!renderedIds.has(source) || !renderedIds.has(target)) continue;
    if (source === target && e.source !== e.target) continue;
    const id = `${source}->${target}:${e.kind}`;
    if (seenEdgeIds.has(id)) continue;
    seenEdgeIds.add(id);
    edges.push({ data: { id, source, target, kind: e.kind } });
  }
  return { nodes, edges };
}

function strongestDescendantStatus(fileId, nodes, parentOf) {
  const rankOf = (status) => {
    const rank = STATUS_RANK.indexOf(status);
    return rank === -1 ? STATUS_RANK.length : rank;
  };
  let strongest = "unchanged";
  for (const n of nodes) {
    for (let ancestor = parentOf.get(n.id); ancestor; ancestor = parentOf.get(ancestor)) {
      if (ancestor === fileId && rankOf(n.status) < rankOf(strongest)) strongest = n.status;
    }
  }
  return strongest;
}

function changedAndBlastRadiusIds(nodes, parentOf) {
  const revealed = new Set();
  for (const node of nodes) {
    if (node.status === "unchanged") continue;
    revealed.add(node.id);
    for (let ancestor = parentOf.get(node.id); ancestor; ancestor = parentOf.get(ancestor)) {
      revealed.add(ancestor);
    }
  }
  return revealed;
}

function setChangedOnlyView(enabled) {
  changedOnlyView = enabled;
  if (graphData) renderGraph(toElements(graphData));
}

function toggleFileCollapsed(fileId) {
  if (collapsedFileIds.has(fileId)) collapsedFileIds.delete(fileId);
  else collapsedFileIds.add(fileId);
  renderGraph(toElements(graphData));
}

function sameTopology(elements) {
  const wanted = new Set([
    ...elements.nodes.map((n) => n.data.id),
    ...elements.edges.map((e) => e.data.id),
  ]);
  const current = cy.elements().map((ele) => ele.id());
  return current.length === wanted.size && current.every((id) => wanted.has(id));
}

function renderGraph(elements) {
  // Carry node positions across rebuilds so collapse/expand and refreshes
  // adjust the map instead of rescrambling it; nodes new to the view start
  // at their nearest surviving ancestor.
  const previousPositions = new Map();
  if (cy) {
    cy.nodes().forEach((n) => previousPositions.set(n.id(), { ...n.position() }));
    cy.destroy();
  }
  const parentOf = new Map(elements.nodes.map((n) => [n.data.id, n.data.parent]));
  for (const node of elements.nodes) {
    for (let id = node.data.id; id; id = parentOf.get(id)) {
      const position = previousPositions.get(id);
      if (position) {
        node.position = { ...position };
        break;
      }
    }
  }
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
        selector: "node[kind='file'][collapsedStatus]",
        style: {
          "background-color": (ele) => COLORS[ele.data("collapsedStatus")] || COLORS.unchanged,
          "background-opacity": 1,
          "border-color": (ele) => COLORS[ele.data("collapsedStatus")] || COLORS.unchanged,
          "text-valign": "center",
          "text-margin-y": 0,
          padding: "7px",
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
    layout: layoutOptions(previousPositions.size > 0),
  });
  // fcose measures label-sized childless nodes before fonts resolve, which
  // caches them as zero-width/invisible; recomputing styles clears that.
  cy.nodes().updateStyle();
  window.cy = cy; // console/debugging access
  cy.on("tap", "node", (evt) => {
    selectedId = evt.target.id();
    showDetails(nodesById[selectedId]);
  });
  cy.on("tap", (evt) => {
    if (evt.target === cy) clearDetails();
  });
  cy.on("dbltap", "node[kind='file']", (evt) => toggleFileCollapsed(evt.target.id()));
}

function layoutOptions(keepPositions) {
  // fcose packs compound (file/class) boxes tightly around their children,
  // so box size tracks content instead of layout scatter.
  return {
    name: "fcose",
    animate: false,
    quality: "proof",
    randomize: !keepPositions,
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

document.getElementById("changed-only").addEventListener("change", (event) => {
  setChangedOnlyView(event.target.checked);
});

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
