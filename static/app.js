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
// Files default to collapsed when nothing inside needs review; a manual
// double-click overrides the default for that file until the file goes away.
const userCollapsedFileIds = new Set();
const userExpandedFileIds = new Set();
let changedOnlyView = false;
let hideTestsView = true;
let showImportsView = false;
let showCallsView = false;

async function loadGraph() {
  const res = await fetch("/api/graph");
  const data = await res.json();
  currentHash = data.hash;
  graphData = data;
  nodesById = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  for (const overrides of [userCollapsedFileIds, userExpandedFileIds]) {
    for (const id of [...overrides]) {
      if (!nodesById[id] || nodesById[id].kind !== "file") overrides.delete(id);
    }
  }
  document.getElementById("paths").innerHTML =
    `agent workspace: ${esc(data.staged)}<br>your tree: ${esc(data.base)}`;
  renderBanner(data.meta && data.meta.rationale ? data.meta.rationale.message : null);

  const elements = toElements(data);
  if (cy && sameTopology(elements)) {
    for (const n of elements.nodes) {
      const ele = cy.getElementById(n.data.id);
      ele.data("status", n.data.status);
      if (n.data.collapsedStatus) ele.data("collapsedStatus", n.data.collapsedStatus);
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
  const strongestStatus = strongestDescendantStatusByAncestor(data.nodes, parentOf);
  const collapsedFileIds = effectiveCollapsedFileIds(data.nodes, strongestStatus);

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
    .filter((n) => representativeId(n.id) === n.id
      && (!revealedIds || revealedIds.has(n.id))
      && (!hideTestsView || !isTestPath(n.path)))
    .map((n) => {
      const nodeData = { id: n.id, label: n.label, kind: n.kind, status: n.status, parent: n.parent || undefined };
      if (collapsedFileIds.has(n.id)) {
        nodeData.collapsedStatus = strongestStatus.get(n.id) || "unchanged";
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
    if (e.kind === "imports" && !showImportsView) continue;
    if (e.kind === "calls" && !showCallsView) continue;
    const id = `${source}->${target}:${e.kind}`;
    if (seenEdgeIds.has(id)) continue;
    seenEdgeIds.add(id);
    edges.push({ data: { id, source, target, kind: e.kind } });
  }
  return { nodes, edges };
}

function strongestDescendantStatusByAncestor(nodes, parentOf) {
  const rankOf = (status) => {
    const rank = STATUS_RANK.indexOf(status);
    return rank === -1 ? STATUS_RANK.length : rank;
  };
  const strongest = new Map();
  for (const node of nodes) {
    for (let ancestor = parentOf.get(node.id); ancestor; ancestor = parentOf.get(ancestor)) {
      const current = strongest.get(ancestor) || "unchanged";
      if (rankOf(node.status) < rankOf(current)) strongest.set(ancestor, node.status);
    }
  }
  return strongest;
}

function fileNeedsReview(file, strongestStatus) {
  return file.status !== "unchanged"
    || (strongestStatus.get(file.id) || "unchanged") !== "unchanged";
}

function effectiveCollapsedFileIds(nodes, strongestStatus) {
  const collapsed = new Set();
  for (const node of nodes) {
    if (node.kind !== "file") continue;
    if (userCollapsedFileIds.has(node.id)) collapsed.add(node.id);
    else if (userExpandedFileIds.has(node.id)) continue;
    else if (!fileNeedsReview(node, strongestStatus)) collapsed.add(node.id);
  }
  return collapsed;
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

function isTestPath(path) {
  const segments = path.split("/");
  if (segments.some((segment) => segment === "tests" || segment === "test")) return true;
  const filename = segments[segments.length - 1];
  return /^test_.*\.py$/.test(filename) || /_test\.py$/.test(filename);
}

function setHideTestsView(enabled) {
  hideTestsView = enabled;
  if (graphData) renderGraph(toElements(graphData));
}

function setShowImportsView(enabled) {
  showImportsView = enabled;
  if (graphData) renderGraph(toElements(graphData));
}

function setShowCallsView(enabled) {
  showCallsView = enabled;
  if (graphData) renderGraph(toElements(graphData));
}

function toggleFileCollapsed(fileId) {
  const parentOf = new Map(graphData.nodes.map((n) => [n.id, n.parent]));
  const strongestStatus = strongestDescendantStatusByAncestor(graphData.nodes, parentOf);
  const isCollapsed = effectiveCollapsedFileIds(graphData.nodes, strongestStatus).has(fileId);
  if (isCollapsed) {
    userCollapsedFileIds.delete(fileId);
    userExpandedFileIds.add(fileId);
  } else {
    userExpandedFileIds.delete(fileId);
    userCollapsedFileIds.add(fileId);
  }
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
          width: 130,
          "text-wrap": "ellipsis",
          "text-max-width": 120,
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
    layout: layoutOptions(previousPositions.size > 0, elements, graphData),
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

function layoutOptions(keepPositions, elements, data) {
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
    ...layeredPlacementConstraints(data, elements.nodes),
  };
}

// Turns the backend's precomputed `layer` numbers (import depth for files,
// intra-file call depth for top-level functions — see graphwerk/layout.py)
// into fcose banding constraints for whatever is currently visible.
function layeredPlacementConstraints(data, nodes) {
  const layerOf = new Map(data.nodes.map((n) => [n.id, n.layer]));
  const orderOf = new Map(data.nodes.map((n) => [n.id, n.order]));
  const anchorOf = simpleConstraintAnchors(nodes);

  const fileAnchorsByLayer = new Map();
  const functionAnchorsByLayerPerFile = new Map();
  for (const node of nodes) {
    const layer = layerOf.get(node.data.id);
    if (layer == null) continue;
    const order = orderOf.get(node.data.id);
    if (node.data.kind === "file") {
      addAnchor(fileAnchorsByLayer, layer, anchorOf(node.data.id), order);
    } else if (node.data.kind === "function") {
      if (!functionAnchorsByLayerPerFile.has(node.data.parent)) {
        functionAnchorsByLayerPerFile.set(node.data.parent, new Map());
      }
      addAnchor(functionAnchorsByLayerPerFile.get(node.data.parent), layer, node.data.id, order);
    }
  }

  const alignments = [];
  const relativePlacementConstraint = [];
  appendBandConstraints(anchorsSortedByOrder(fileAnchorsByLayer), 220, alignments, relativePlacementConstraint);
  for (const anchorsByLayer of functionAnchorsByLayerPerFile.values()) {
    // function chips are smaller than file boxes, so their bands sit closer
    appendBandConstraints(anchorsSortedByOrder(anchorsByLayer), 75, alignments, relativePlacementConstraint);
  }

  if (!alignments.length) return {};
  return { alignmentConstraint: { horizontal: alignments }, relativePlacementConstraint };
}

function addAnchor(anchorsByLayer, layer, anchor, order) {
  if (!anchorsByLayer.has(layer)) anchorsByLayer.set(layer, []);
  anchorsByLayer.get(layer).push({ anchor, order });
}

// The left-right chain pins each band's sequence, so chain in the backend's
// barycenter `order` (ADR 008); nodes without one keep insertion order, last.
function anchorsSortedByOrder(entriesByLayer) {
  const anchorsByLayer = new Map();
  for (const [layer, entries] of entriesByLayer) {
    const rank = (entry) => (entry.order == null ? Number.MAX_SAFE_INTEGER : entry.order);
    const sorted = [...entries].sort((a, b) => rank(a) - rank(b));
    anchorsByLayer.set(layer, sorted.map((entry) => entry.anchor));
  }
  return anchorsByLayer;
}

// Deeper layers (entry points, callers) render above what they depend on;
// one representative per layer pair suffices vertically since
// alignmentConstraint already ties every member of a layer to one band.
// Members of a layer chain left-to-right with a minimum gap so same-band
// nodes don't crowd — alignment only fixes their shared y, not spacing.
function appendBandConstraints(anchorsByLayer, verticalGap, alignments, relativePlacements) {
  if (anchorsByLayer.size < 2) return;
  const layersDeepestFirst = [...anchorsByLayer.keys()].sort((a, b) => b - a);
  for (let i = 0; i < layersDeepestFirst.length - 1; i++) {
    relativePlacements.push({
      top: anchorsByLayer.get(layersDeepestFirst[i])[0],
      bottom: anchorsByLayer.get(layersDeepestFirst[i + 1])[0],
      gap: verticalGap,
    });
  }
  for (const anchors of anchorsByLayer.values()) {
    for (let i = 0; i < anchors.length - 1; i++) {
      relativePlacements.push({ left: anchors[i], right: anchors[i + 1], gap: 190 });
    }
    alignments.push(anchors);
  }
}

// fcose's alignment/relative-placement constraints only accept "simple"
// (childless) node ids, never a compound (expanded file/class) node itself
// — so an expanded file is represented by one of its leaf descendants,
// which the compound-gravity forces keep nested inside the file's box.
function simpleConstraintAnchors(nodes) {
  const childrenOf = new Map();
  for (const node of nodes) {
    if (!node.data.parent) continue;
    if (!childrenOf.has(node.data.parent)) childrenOf.set(node.data.parent, []);
    childrenOf.get(node.data.parent).push(node.data.id);
  }
  return function anchorOf(id) {
    let current = id;
    while (childrenOf.has(current)) current = childrenOf.get(current)[0];
    return current;
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

  const codeSection = document.getElementById("code-section");
  const hasCode = Array.isArray(node.code) && node.code.length > 0;
  codeSection.hidden = !hasCode;
  if (hasCode) document.getElementById("d-code").innerHTML = renderCode(node.code);

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

function renderCode(lines) {
  const rows = lines.map((line) =>
    `<div class="row ${line.op}"><span class="ln">${line.line}</span><span class="lt">${renderLineText(line) || " "}</span></div>`
  );
  return `<div class="lines">${rows.join("")}</div>`;
}

function renderLineText(line) {
  let html = "";
  let cursor = 0;
  for (const [start, end, cls] of line.spans) {
    html += esc(line.text.slice(cursor, start));
    html += `<span class="${cls}">${esc(line.text.slice(start, end))}</span>`;
    cursor = end;
  }
  return html + esc(line.text.slice(cursor));
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

// Dismissal is per message: a new server message reopens the banner.
let dismissedBannerMessage = null;
function renderBanner(message) {
  const banner = document.getElementById("banner");
  banner.hidden = !message || message === dismissedBannerMessage;
  if (!banner.hidden) document.getElementById("banner-text").textContent = message;
}

document.getElementById("banner-dismiss").addEventListener("click", () => {
  dismissedBannerMessage = document.getElementById("banner-text").textContent;
  document.getElementById("banner").hidden = true;
});

function renderSessionState(session) {
  const running = session.state === "running";
  document.getElementById("prompt-input").disabled = running;
  document.getElementById("prompt-send").disabled = running;
  document.getElementById("prompt-busy").hidden = !running;
  const error = document.getElementById("prompt-error");
  error.hidden = session.state !== "failed";
  if (session.state === "failed") error.textContent = session.detail;
}

document.getElementById("prompt-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("prompt-input");
  const promptText = input.value.trim();
  if (!promptText) return;
  const res = await fetch("/api/prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: promptText }),
  });
  const data = await res.json();
  if (res.ok) {
    input.value = "";
    renderSessionState(data);
  } else if (res.status === 409) {
    renderSessionState({ state: "running" });
  } else {
    renderSessionState({ state: "failed", detail: data.detail });
  }
});

document.getElementById("changed-only").addEventListener("change", (event) => {
  setChangedOnlyView(event.target.checked);
});

document.getElementById("hide-tests").addEventListener("change", (event) => {
  setHideTestsView(event.target.checked);
});

document.getElementById("show-imports").addEventListener("change", (event) => {
  setShowImportsView(event.target.checked);
});

document.getElementById("show-calls").addEventListener("change", (event) => {
  setShowCallsView(event.target.checked);
});

setInterval(async () => {
  try {
    const res = await fetch("/api/hash");
    const data = await res.json();
    if (data.hash !== currentHash) loadGraph();
    const sessionRes = await fetch("/api/session");
    renderSessionState(await sessionRes.json());
  } catch {
    /* server briefly unreachable; keep polling */
  }
}, 1500);


loadGraph();
