/* graphwerk review UI: Cytoscape graph + review sidebar.
 * Polls /api/hash; refetches the graph whenever either tree changes. */

const COLORS = {
  modified: "#22c55e",
  added: "#3b82f6",
  deleted: "#ef4444",
  affected: "#f59e0b",
  unchanged: "#475569",
};

const STATUS_RANK = ["modified", "added", "deleted", "affected", "unchanged"];

function statusRank(status) {
  const rank = STATUS_RANK.indexOf(status);
  return rank === -1 ? STATUS_RANK.length : rank;
}

// Muted, dark-theme-friendly fills for the directory tint (ADR 010) — kept
// visually distinct from the saturated status colors above, which stay on
// borders.
const GROUP_TINT_PALETTE = [
  "#4c1d95", "#164e63", "#7c2d12", "#365314",
  "#831843", "#1e3a8a", "#78350f", "#134e4a",
];

let cy = null;
let currentHash = null;
let loadGraphInFlight = false;
let graphData = null;
let nodesById = {};
let selectedId = null;
// Which edge-calls panel is open, mirroring selectedId for nodes — lets the
// code-mode toggle re-render whichever panel (node or edge) is current.
let selectedEdgeId = null;
// "full" (code + changes, today's default), "changed-methods" (only
// changed leaf function/method symbols, each shown full-context under its
// own heading), or "changes-only" — a shared filter applied wherever
// renderCode is called (ADR 028, ADR 051).
let codeDisplayMode = "changed-methods";
// Every container (file or class) starts collapsed; a double-click expands
// it for the session until the node goes away.
const userExpandedIds = new Set();
let changedOnlyView = false;
let hideTestsView = true;
let showImportsView = false;
let showCallsView = true;
// "design" | "implementation" — filters rendered nodes by domain
// and doubles as the scope sent with the next spawned session (ADR 046).
let domainModeView = "implementation";
// group -> tint color, assigned in first-seen payload order (ADR 010).
let groupTints = new Map();
// Edges kept visible by a click, independent of hover; cleared by tapping
// empty canvas (mirrors clearDetails' existing selection-reset gesture).
const pinnedEdgeIds = new Set();
// The node whose neighborhood is currently isolated (ticket 153); null means
// every node is visible. Cleared by tapping empty canvas, recomputed by
// tapping a different node.
let isolatedNodeId = null;
// Recomputed on every loadGraph() from the server-held ApprovalStore (ADR
// 050) — never client-tracked, so a reload always shows the real count.
let approvedFileCount = 0;
// Mirrors renderSessionState's busy check; kept alongside approvedFileCount
// since the commit button's disabled state depends on both.
let sessionBusy = false;

async function loadGraph() {
  if (loadGraphInFlight) return;
  loadGraphInFlight = true;
  try {
    const res = await fetch("/api/graph");
    const data = await res.json();
    currentHash = data.hash;
    graphData = data;
    nodesById = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
    for (const id of [...userExpandedIds]) {
      const node = nodesById[id];
      if (!node || (node.kind !== "file" && node.kind !== "class")) userExpandedIds.delete(id);
    }
    document.getElementById("paths").innerHTML =
      `agent workspace: ${esc(data.staged)}<br>your tree: ${esc(data.base)}`;
    renderBanner(data.meta && data.meta.rationale ? data.meta.rationale.message : null);
    minedCommitMessage = data.meta ? data.meta.commit_message : null;
    maybeFillCommitMessageBox();

    groupTints = buildGroupTints(data.nodes);
    renderGroupLegend(groupTints);

    approvedFileCount = data.nodes.filter((n) => n.kind === "file" && n.approved).length;
    renderCommitButton();

    const elements = toElements(data);
    if (cy && sameTopology(elements)) {
      for (const n of elements.nodes) {
        const ele = cy.getElementById(n.data.id);
        ele.data("status", n.data.status);
        if (n.data.group != null) ele.data("group", n.data.group);
        if (n.data.collapsedStatus) ele.data("collapsedStatus", n.data.collapsedStatus);
      }
      for (const e of elements.edges) {
        const ele = cy.getElementById(e.data.id);
        ele.data("status", e.data.status);
        ele.data("calls", e.data.calls);
      }
    } else {
      renderGraph(elements);
    }
    if (selectedId) {
      if (nodesById[selectedId]) showDetails(nodesById[selectedId]);
      else clearDetails();
    }
  } finally {
    loadGraphInFlight = false;
  }
}

function toElements(data) {
  const parentOf = new Map(data.nodes.map((n) => [n.id, n.parent]));
  const strongestStatus = strongestDescendantStatusByAncestor(data.nodes, parentOf);
  const collapsedContainerIds = effectiveCollapsedContainerIds(data.nodes, parentOf);

  // A node hidden inside a collapsed container is represented by that
  // container node; everything else represents itself.
  const representativeId = (id) => {
    let representative = id;
    for (let ancestor = parentOf.get(id); ancestor; ancestor = parentOf.get(ancestor)) {
      if (collapsedContainerIds.has(ancestor)) representative = ancestor;
    }
    return representative;
  };

  const revealedIds = changedOnlyView ? changedAndBlastRadiusIds(data.nodes, parentOf) : null;

  // Only signal-free test nodes are hideable: a changed or affected test —
  // itself or via any descendant — is review signal, not noise (ADR 036).
  const signalFreeTestNode = (n) => n.is_test
    && n.status === "unchanged"
    && (strongestStatus.get(n.id) || "unchanged") === "unchanged";

  const nodes = data.nodes
    .filter((n) => representativeId(n.id) === n.id
      && (!revealedIds || revealedIds.has(n.id))
      && (!hideTestsView || !signalFreeTestNode(n))
      && matchesDomainMode(n))
    .map((n) => {
      const nodeData = { id: n.id, label: n.label, kind: n.kind, status: n.status, parent: n.parent || undefined };
      if (n.group != null) nodeData.group = n.group;
      if (n.paired_file != null) nodeData.pairedFile = n.paired_file;
      if (collapsedContainerIds.has(n.id)) {
        nodeData.collapsedStatus = strongestStatus.get(n.id) || "unchanged";
      }
      return { data: nodeData };
    });

  const renderedIds = new Set(nodes.map((n) => n.data.id));
  const edgesById = new Map();
  for (const e of data.edges) {
    const source = representativeId(e.source);
    const target = representativeId(e.target);
    if (!renderedIds.has(source) || !renderedIds.has(target)) continue;
    if (source === target && e.source !== e.target) continue;
    if (e.kind === "imports" && !showImportsView) continue;
    if (e.kind === "calls" && !showCallsView) continue;
    const id = `${source}->${target}:${e.kind}`;
    let edge = edgesById.get(id);
    if (!edge) {
      edge = { data: { id, source, target, kind: e.kind, status: e.status, calls: [] } };
      edgesById.set(id, edge);
    }
    edge.data.calls.push({ source: e.source, target: e.target, status: e.status, module: e.module, via_imports: e.via_imports });
    if (statusRank(e.status) < statusRank(edge.data.status)) edge.data.status = e.status;
  }
  return { nodes, edges: [...edgesById.values()] };
}

function strongestDescendantStatusByAncestor(nodes, parentOf) {
  const strongest = new Map();
  for (const node of nodes) {
    for (let ancestor = parentOf.get(node.id); ancestor; ancestor = parentOf.get(ancestor)) {
      const current = strongest.get(ancestor) || "unchanged";
      if (statusRank(node.status) < statusRank(current)) strongest.set(ancestor, node.status);
    }
  }
  return strongest;
}

function effectiveCollapsedContainerIds(nodes, parentOf) {
  const containerIds = new Set([...parentOf.values()].filter(Boolean));
  const collapsed = new Set();
  for (const node of nodes) {
    if (!containerIds.has(node.id)) continue;
    if (!userExpandedIds.has(node.id)) collapsed.add(node.id);
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

const DOMAIN_BY_MODE = { design: "doc", implementation: "code" };

function matchesDomainMode(node) {
  const wantedDomain = DOMAIN_BY_MODE[domainModeView];
  return !wantedDomain || node.domain === wantedDomain;
}

function setDomainModeView(mode) {
  domainModeView = mode;
  if (graphData) renderGraph(toElements(graphData));
  renderDesignDialogue();
}

// Design-mode dialogue (ADR 047): client-side only, prompt/reply pairs
// accumulated for the tab's lifetime. Reset on a fresh start(), preserved
// across continue_session and across toggling away from Design and back —
// only hidden by the toggle, never cleared by it.
let designDialogue = [];
// The prompt just submitted, waiting for its turn to settle with a reply;
// guards against the runner's `reply` field still holding the *previous*
// turn's text while this turn is running (SessionRunner only updates it on
// settle, same staleness convention as `session_id`).
let pendingDesignDialoguePrompt = null;

function renderDesignDialogue() {
  const panel = document.getElementById("design-dialogue");
  panel.hidden = domainModeView !== "design";
  if (panel.hidden) return;
  const list = document.getElementById("design-dialogue-list");
  list.innerHTML = "";
  for (const turn of designDialogue) {
    const item = document.createElement("li");
    const promptEl = document.createElement("div");
    promptEl.className = "design-dialogue-prompt";
    promptEl.textContent = turn.prompt;
    const replyEl = document.createElement("div");
    replyEl.className = "design-dialogue-reply";
    replyEl.textContent = turn.reply;
    item.append(promptEl, replyEl);
    list.appendChild(item);
  }
  list.scrollTop = list.scrollHeight;
}

function maybeAppendDesignDialogueTurn(session) {
  if (domainModeView !== "design" || !pendingDesignDialoguePrompt) return;
  if (SESSION_BUSY_STATES.includes(session.state)) return;
  const prompt = pendingDesignDialoguePrompt;
  pendingDesignDialoguePrompt = null;
  if (!session.reply) return;
  designDialogue.push({ prompt, reply: session.reply });
  renderDesignDialogue();
}

// Re-renders whichever panel is currently open so the toggle takes effect
// immediately, without the reviewer having to reselect a node or edge.
function setCodeDisplayMode(mode) {
  codeDisplayMode = mode;
  if (selectedId && nodesById[selectedId]) {
    showDetails(nodesById[selectedId]);
  } else if (selectedEdgeId && cy) {
    const edge = cy.getElementById(selectedEdgeId);
    if (edge.empty()) return;
    if (edge.data("kind") === "imports") showEdgeImports(edge);
    else showEdgeCalls(edge);
  }
}

function toggleContainerCollapsed(containerId) {
  const parentOf = new Map(graphData.nodes.map((n) => [n.id, n.parent]));
  const isCollapsed = effectiveCollapsedContainerIds(graphData.nodes, parentOf).has(containerId);
  if (isCollapsed) userExpandedIds.add(containerId);
  else userExpandedIds.delete(containerId);
  renderGraph(toElements(graphData));
}

function pinEdges(edgeCollection) {
  edgeCollection.forEach((edge) => pinnedEdgeIds.add(edge.id()));
  edgeCollection.addClass("pinned");
}

function unpinAllEdges() {
  pinnedEdgeIds.clear();
  cy.edges().removeClass("pinned");
}

// Classes don't survive renderGraph's destroy/recreate; reapply after a
// rebuild and drop ids for edges that no longer exist in the new graph.
function applyPinnedEdges() {
  for (const id of [...pinnedEdgeIds]) {
    const edge = cy.getElementById(id);
    if (edge.empty()) pinnedEdgeIds.delete(id);
    else edge.addClass("pinned");
  }
}

// The tapped node itself, its compound ancestors, its own descendants (an
// expanded container's contents), every node joined to it by an edge
// currently in the Cytoscape instance (regardless of that edge's own
// hover/pinned/unchanged display state), and those neighbors' own compound
// ancestors (ADR 056).
function computeIsolationKeepSet(nodeId) {
  const node = cy.getElementById(nodeId);
  const keep = new Set([nodeId]);
  node.parents().forEach((ancestor) => keep.add(ancestor.id()));
  node.descendants().forEach((descendant) => keep.add(descendant.id()));
  node.connectedEdges().forEach((edge) => {
    const neighbor = edge.source().same(node) ? edge.target() : edge.source();
    keep.add(neighbor.id());
    neighbor.parents().forEach((ancestor) => keep.add(ancestor.id()));
  });
  return keep;
}

function setIsolatedNode(nodeId) {
  isolatedNodeId = nodeId;
  applyNodeIsolation();
}

// Classes don't survive renderGraph's destroy/recreate; reapply after a
// rebuild, mirroring applyPinnedEdges().
function applyNodeIsolation() {
  cy.nodes().removeClass("isolation-hidden");
  if (!isolatedNodeId) return;
  if (cy.getElementById(isolatedNodeId).empty()) {
    isolatedNodeId = null;
    return;
  }
  const keepSet = computeIsolationKeepSet(isolatedNodeId);
  cy.nodes().filter((n) => !keepSet.has(n.id())).addClass("isolation-hidden");
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
    wheelSensitivity: 5,
    minZoom: 0.15,
    maxZoom: 3,
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
          "background-color": (ele) => tintFor(ele.data("group")),
          "background-opacity": 0.6,
          "border-width": 2,
          "border-color": (ele) => COLORS[ele.data("status")] || "#334155",
          padding: "14px",
        },
      },
      {
        selector: "node[collapsedStatus]",
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
        // Collapsed file chips keep the tint as their fill; status moves
        // fully onto the border (widened since the fill no longer carries it).
        selector: "node[collapsedStatus][kind='file']",
        style: {
          "background-color": (ele) => tintFor(ele.data("group")),
          "background-opacity": 0.7,
          "border-width": 2.5,
        },
      },
      {
        selector: "node[status='deleted'], node[collapsedStatus='deleted']",
        style: { "border-style": "dashed", opacity: 0.6 },
      },
      {
        // Node-click isolation (ADR 056): hides everything outside the
        // tapped node's keep set without removing it from the graph.
        selector: "node.isolation-hidden",
        style: { display: "none" },
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
        selector: "edge[kind='calls']",
        style: {
          "line-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
          "target-arrow-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
        },
      },
      {
        selector: "edge[kind='imports']",
        style: {
          "line-style": "dashed",
          "line-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
          "target-arrow-color": (ele) => COLORS[ele.data("status")] || COLORS.unchanged,
        },
      },
      {
        // Unchanged edges (all imports edges, most calls edges) are clutter,
        // not review signal — hidden by default, revealed per-node on hover
        // (ADR 020). Class selectors outrank data selectors in Cytoscape's
        // specificity order, so .revealed wins over this rule while active.
        selector: "edge[status='unchanged']",
        style: { display: "none" },
      },
      { selector: "edge.revealed, edge.pinned", style: { display: "element" } },
      { selector: "node:selected", style: { "border-color": "#f8fafc", "border-width": 3 } },
    ],
    layout: layoutOptions(previousPositions.size > 0, elements, graphData),
  });
  // fcose measures label-sized childless nodes before fonts resolve, which
  // caches them as zero-width/invisible; recomputing styles clears that.
  cy.nodes().updateStyle();
  // The initial layout (passed via the `layout:` constructor option above)
  // runs and emits "layoutstop" synchronously before this function gets a
  // chance to register a listener for it, so paired-test placement is
  // called directly here instead of via that event — after updateStyle()
  // so the width()/height() reads below see resolved label sizes.
  placePairedTestNodes();
  window.cy = cy; // console/debugging access
  cy.on("tap", "node", (evt) => {
    selectedId = evt.target.id();
    showDetails(nodesById[selectedId]);
    pinEdges(evt.target.connectedEdges());
    setIsolatedNode(selectedId);
  });
  cy.on("tap", "edge", (evt) => pinEdges(evt.target));
  cy.on("tap", "edge[kind='calls']", (evt) => showEdgeCalls(evt.target));
  cy.on("tap", "edge[kind='imports']", (evt) => showEdgeImports(evt.target));
  cy.on("tap", (evt) => {
    if (evt.target === cy) {
      clearDetails();
      unpinAllEdges();
      setIsolatedNode(null);
    }
  });
  cy.on("dbltap", "node[kind='file'], node[kind='class']", (evt) => toggleContainerCollapsed(evt.target.id()));
  cy.on("mouseover", "node", (evt) => evt.target.connectedEdges().addClass("revealed"));
  cy.on("mouseout", "node", (evt) => evt.target.connectedEdges().removeClass("revealed"));
  applyPinnedEdges();
  applyNodeIsolation();
}

// fcose has no "my left edge equals your center" primitive (ADR 041), so a
// paired test pill is snapped into place after the layout settles instead of
// being expressed as a layout constraint; reads the file node's actual
// rendered box so this works whether the file is collapsed or expanded.
const PAIRED_TEST_GAP = 24;

function placePairedTestNodes() {
  cy.nodes("[pairedFile]").forEach((testNode) => {
    const fileNode = cy.getElementById(testNode.data("pairedFile"));
    if (fileNode.empty()) return;
    testNode.position({
      x: fileNode.position("x") + testNode.width() / 2,
      y: fileNode.position("y") + fileNode.height() / 2 + PAIRED_TEST_GAP,
    });
  });
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

// Layer 0 (entry points, callers) renders above what it depends on; one
// representative per layer pair suffices vertically since
// alignmentConstraint already ties every member of a layer to one band.
// Members of a layer chain left-to-right with a minimum gap so same-band
// nodes don't crowd — alignment only fixes their shared y, not spacing.
function appendBandConstraints(anchorsByLayer, verticalGap, alignments, relativePlacements) {
  if (anchorsByLayer.size < 2) return;
  const layersTopFirst = [...anchorsByLayer.keys()].sort((a, b) => a - b);
  for (let i = 0; i < layersTopFirst.length - 1; i++) {
    relativePlacements.push({
      top: anchorsByLayer.get(layersTopFirst[i])[0],
      bottom: anchorsByLayer.get(layersTopFirst[i + 1])[0],
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
  selectedEdgeId = null;
  document.getElementById("placeholder").hidden = true;
  document.getElementById("edge-calls").hidden = true;
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
  document.getElementById("d-why-confidence").hidden = node.why_confident !== false;
  document.getElementById("d-why-justifies").hidden = node.why_justifies !== false;

  const codeSection = document.getElementById("code-section");
  const changedMethods = codeDisplayMode === "changed-methods" ? changedLeafDescendants(node.id) : [];
  const hasCode = changedMethods.length > 0 || (Array.isArray(node.code) && node.code.length > 0);
  codeSection.hidden = !hasCode;
  if (changedMethods.length > 0) {
    document.getElementById("d-code").innerHTML = renderChangedMethods(changedMethods);
  } else if (hasCode) {
    document.getElementById("d-code").innerHTML = renderCode(node.code);
  }

  const changed = ["modified", "added", "deleted"].includes(node.status);
  const applyBtn = document.getElementById("btn-apply");
  applyBtn.hidden = !changed;
  applyBtn.textContent = node.approved ? `Unapprove file ${node.path}` : `Approve file ${node.path}`;
  applyBtn.onclick = () => toggleApproval(node.path, node.approved);

  document.getElementById("reject-box").hidden = !changed;
  document.getElementById("reject-result").hidden = true;
  document.getElementById("btn-reject").onclick = () => rejectNode(node);
}

function clearDetails() {
  selectedId = null;
  selectedEdgeId = null;
  document.getElementById("placeholder").hidden = false;
  document.getElementById("details").hidden = true;
  document.getElementById("edge-calls").hidden = true;
}

// The raw graph id is "<rel_path>::<qualname>"; the qualname alone (e.g.
// "PaymentValidator.charge") is more legible here than the file-qualified id.
function qualifiedLabel(nodeId) {
  const separator = nodeId.indexOf("::");
  return separator === -1 ? nodeId : nodeId.slice(separator + 2);
}

function showEdgeCalls(edge) {
  selectedId = null;
  selectedEdgeId = edge.id();
  document.getElementById("placeholder").hidden = true;
  document.getElementById("details").hidden = true;
  document.getElementById("edge-calls").hidden = false;
  document.getElementById("edge-calls-title").textContent = "Calls collapsed onto this edge";
  const calls = edge.data("calls");
  document.getElementById("d-calls").innerHTML = calls.map(renderCallPair).join("");
}

// Deliberately not the full file diff (already one click away via the file
// node itself) — just which module(s) were added/removed for this file
// pair, reusing the calls panel markup (ADR 033).
function showEdgeImports(edge) {
  selectedId = null;
  selectedEdgeId = edge.id();
  document.getElementById("placeholder").hidden = true;
  document.getElementById("details").hidden = true;
  document.getElementById("edge-calls").hidden = false;
  document.getElementById("edge-calls-title").textContent = "Imports collapsed onto this edge";
  const imports = edge.data("calls");
  document.getElementById("d-calls").innerHTML = imports.map(renderImportEntry).join("");
}

// Entries without a `code` field (the imports-edge panel, or an extractor
// that captured no statement) keep the chip + module-name fallback (ADR 038).
// A `file` field (ADR 048's multi-hop chain) names which file that hop
// resolves to; single-hop entries never carry it, so their rendering is
// unchanged.
function renderImportEntry({ module, status, code, file }) {
  const badge = `<span class="chip ${status}">${status}</span>`;
  const hop = file ? `<span class="hop-file">&rarr; ${esc(file)}</span> ` : "";
  if (Array.isArray(code) && code.length > 0) {
    return `<div class="import-entry">${badge}${hop}<div class="code">${renderCode(code)}</div></div>`;
  }
  const sign = status === "deleted" ? "-" : status === "added" ? "+" : " ";
  return `<div class="import-entry">${badge} ${hop}${sign} ${esc(module)}</div>`;
}

// One closed-by-default <details> per call pair: the summary is the label,
// the body is that pair's code — no separate deduped code block, so a pair
// you open is always the pair whose code you see (ADR 028). The status badge
// reads the edge's own precomputed status (ADR 016) rather than the nodes'
// status — a source can be "affected" overall via some *other* call while
// this specific pair is genuinely unchanged, and the badge must reflect this
// pair, not the whole node.
function renderCallPair({ source, target, status, via_imports }) {
  const badge = `<span class="chip ${status}">${status}</span>`;
  const summary = `${badge} ${esc(qualifiedLabel(source))} &rarr; ${esc(qualifiedLabel(target))}`;
  const admittingImports = (via_imports || [])
    .filter((entry) => !entry.in_caller_code)
    .map(renderImportEntry)
    .join("");
  const body = [source, target]
    .map((id) => ({ id, node: nodesById[id], imports: id === source ? admittingImports : "" }))
    .filter(({ node }) => node && Array.isArray(node.code) && node.code.length > 0)
    .map(({ id, node, imports }) => `<section><h3>${esc(qualifiedLabel(id))}</h3>${imports}<div class="code">${renderCode(node.code)}</div></section>`)
    .join("");
  return `<details class="call-pair"><summary>${summary}</summary>${body}</details>`;
}

async function toggleApproval(path, currentlyApproved) {
  const endpoint = currentlyApproved ? "/api/unapprove" : "/api/apply";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  const data = await res.json();
  toast(res.ok ? `✓ ${data.approved ? "approved" : "unapproved"} ${path}` : `error: ${data.detail}`);
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

// The leaf symbol kinds "changed methods" mode narrows a container down to
// — whatever the language extractor calls its deepest units (ADR 051).
const CHANGED_LEAF_KINDS = new Set(["function", "method"]);

// Mirrors the Python-side CHANGED set (graphwerk/service.py) — "affected"
// (unchanged itself, but calls into changed code) is a blast-radius signal,
// not a change, and must not count as a "changed method" (ticket 146).
const CHANGED_LEAF_STATUSES = new Set(["modified", "added", "deleted"]);

// Changed leaf symbols nested under `containerId`, found by walking each
// candidate's parent chain in the full (unfiltered) node index — independent
// of the current graph view/collapse state, so it matches whatever the
// backend actually diffed rather than what's currently rendered.
function changedLeafDescendants(containerId) {
  return graphData.nodes.filter((n) =>
    CHANGED_LEAF_KINDS.has(n.kind) && CHANGED_LEAF_STATUSES.has(n.status) && isDescendant(n.id, containerId)
  );
}

function isDescendant(nodeId, ancestorId) {
  for (let id = nodesById[nodeId] && nodesById[nodeId].parent; id; id = nodesById[id] && nodesById[id].parent) {
    if (id === ancestorId) return true;
  }
  return false;
}

// Stacks each changed leaf symbol's own already-computed `code` view under
// a heading naming it, instead of the container's single merged view.
function renderChangedMethods(symbols) {
  return symbols
    .map((symbol) => `<div class="changed-method"><h4>${esc(qualifiedLabel(symbol.id))}</h4>${renderCode(symbol.code)}</div>`)
    .join("");
}

function renderCode(lines) {
  const rows = codeModeLines(lines).map((line) =>
    `<div class="row ${line.op}"><span class="ln">${line.line}</span><span class="lt">${renderLineText(line) || " "}</span></div>`
  );
  return `<div class="lines">${rows.join("")}</div>`;
}

// "changes-only" strips context lines; a panel that would go empty (a
// genuinely unchanged node, all-context by construction) falls back to the
// full view instead of rendering nothing.
function codeModeLines(lines) {
  if (codeDisplayMode !== "changes-only") return lines;
  const changed = lines.filter((line) => line.op === "add" || line.op === "del");
  return changed.length > 0 ? changed : lines;
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

function buildGroupTints(nodes) {
  const tints = new Map();
  for (const node of nodes) {
    if (node.kind !== "file" || node.group == null || tints.has(node.group)) continue;
    tints.set(node.group, GROUP_TINT_PALETTE[tints.size % GROUP_TINT_PALETTE.length]);
  }
  return tints;
}

function tintFor(group) {
  return groupTints.get(group) || "#1e293b";
}

// Single-package repos and the demo (one group) stay visually unchanged.
function renderGroupLegend(tints) {
  const legend = document.getElementById("group-legend");
  legend.hidden = tints.size < 2;
  legend.innerHTML = [...tints.entries()]
    .map(([group, color]) => `<span><i class="dot" style="background:${color}"></i>${esc(group)}</span>`)
    .join("");
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

// Busy spans the whole check-gate cycle (ADR 040), not just the agent
// subprocess — the prompt bar re-enables only once the cycle hands back.
const SESSION_BUSY_STATES = ["running", "checking", "resuming"];
const SESSION_BUSY_LABELS = { running: "agent session running", checking: "validating…" };

function renderSessionState(session) {
  const busy = SESSION_BUSY_STATES.includes(session.state);
  document.getElementById("prompt-input").disabled = busy;
  document.getElementById("prompt-send").disabled = busy;
  sessionBusy = busy;
  renderCommitButton();
  document.getElementById("btn-discard").disabled = busy;
  const continueCheckbox = document.getElementById("continue-session");
  continueCheckbox.disabled = busy || !session.session_id;
  if (continueCheckbox.disabled) continueCheckbox.checked = false;
  renderSessionBusyIndicator(session, busy);
  const error = document.getElementById("prompt-error");
  error.hidden = session.state !== "failed";
  if (session.state === "failed") error.textContent = session.detail;
  renderCheckBanner(session);
  renderChecksIndicator(session);
  if ((session.state === "done" || session.state === "check_failed") && session.session_id
      && session.session_id !== completedSessionId) {
    completedSessionId = session.session_id;
    // the mined message in hand predates this session — refetch to re-mine
    minedCommitMessage = null;
    loadGraph();
    if (session.state === "done" && session.check_configured) toast(formatCheckPassedToast(session));
  }
  maybeFillCommitMessageBox();
  maybeAppendDesignDialogueTurn(session);
}

function formatCheckCounts(summary) {
  return summary && summary.passed != null && summary.total != null
    ? `${summary.passed}/${summary.total}`
    : null;
}

function formatCheckPassedToast(session) {
  const counts = formatCheckCounts(session.check_summary);
  const parts = [counts ? `${counts} checks passed` : "checks passed"];
  if (session.check_duration_s != null) parts.push(`in ${session.check_duration_s.toFixed(1)}s`);
  return `✓ ${parts.join(" ")}`;
}

// Counts/duration are only shown once a check_summary has actually arrived —
// see ticket 123 (a duration with no summary shouldn't imply pass/fail counts).
function formatCheckCountsAndDuration(session) {
  if (!session.check_summary) return "";
  const parts = [formatCheckCounts(session.check_summary)];
  if (session.check_duration_s != null) parts.push(`in ${session.check_duration_s.toFixed(1)}s`);
  const detail = parts.filter(Boolean).join(" ");
  return detail ? ` (${detail})` : "";
}

const CHECKS_RUNNING_LABELS = { checking: "running…" };

function renderChecksIndicator(session) {
  const el = document.getElementById("checks-indicator");
  if (session.check_configured === false) {
    setChecksIndicator(el, "not-configured", "Checks: not configured");
  } else if (session.state === "checking" || session.state === "resuming") {
    const label = session.state === "resuming"
      ? `retrying — attempt ${session.attempt}…`
      : CHECKS_RUNNING_LABELS.checking;
    setChecksIndicator(el, "running", `Checks: ${label}`);
  } else if (session.state === "done") {
    setChecksIndicator(el, "passed", `Checks: passed${formatCheckCountsAndDuration(session)}`);
  } else if (session.state === "check_failed") {
    setChecksIndicator(el, "failed", `Checks: failed${formatCheckCountsAndDuration(session)}`);
  } else {
    setChecksIndicator(el, "pending", "Checks: pending");
  }
}

function setChecksIndicator(el, variant, text) {
  el.textContent = text;
  el.className = `checks-${variant}`;
}

function renderSessionBusyIndicator(session, busy) {
  const busyEl = document.getElementById("prompt-busy");
  busyEl.hidden = !busy;
  if (!busy) return;
  const label = session.state === "resuming"
    ? `retrying — attempt ${session.attempt}…`
    : (SESSION_BUSY_LABELS[session.state] || session.state);
  document.getElementById("prompt-busy-text").textContent = label;
}

// Dismissal is per check failure: a new failed check reopens the banner.
let dismissedCheckFailureKey = null;
let shownCheckFailureKey = null;

function renderCheckBanner(session) {
  const banner = document.getElementById("check-banner");
  if (session.state !== "check_failed") {
    banner.hidden = true;
    return;
  }
  shownCheckFailureKey = `${session.check_exit_code}:${session.check_tail}`;
  banner.hidden = shownCheckFailureKey === dismissedCheckFailureKey;
  if (banner.hidden) return;
  document.getElementById("check-banner-text").textContent = session.check_exit_code === null
    ? "check could not run"
    : `check failed — exit code ${session.check_exit_code}`;
  document.getElementById("check-banner-tail").textContent = session.check_tail;
  renderCheckBannerSummary(session.check_summary);
}

function renderCheckBannerSummary(summary) {
  const summaryEl = document.getElementById("check-banner-summary");
  const failuresEl = document.getElementById("check-banner-failures");
  const counts = summary
    ? ["passed", "failed", "total"]
        .filter((key) => summary[key] != null)
        .map((key) => `${summary[key]} ${key}`)
    : [];
  summaryEl.hidden = counts.length === 0;
  summaryEl.textContent = counts.join(", ");
  const failures = (summary && summary.failures) || [];
  failuresEl.hidden = failures.length === 0;
  failuresEl.innerHTML = "";
  for (const name of failures) {
    const item = document.createElement("li");
    item.textContent = name;
    failuresEl.appendChild(item);
  }
}

document.getElementById("check-banner-dismiss").addEventListener("click", () => {
  dismissedCheckFailureKey = shownCheckFailureKey;
  document.getElementById("check-banner").hidden = true;
});

// The box is overwritten only when a *new* session's mined message arrives;
// routine refetches never clobber the reviewer's edits (ADR 037).
let completedSessionId = null;
let filledForSessionId = null;
let minedCommitMessage = null;

function maybeFillCommitMessageBox() {
  if (!completedSessionId || completedSessionId === filledForSessionId) return;
  if (minedCommitMessage == null) return;
  document.getElementById("commit-message").value = minedCommitMessage;
  filledForSessionId = completedSessionId;
}

function showCommitError(message) {
  const error = document.getElementById("commit-error");
  error.hidden = !message;
  error.textContent = message || "";
}

function renderCommitButton() {
  const btn = document.getElementById("btn-commit");
  btn.textContent = `Commit ${approvedFileCount} approved file${approvedFileCount === 1 ? "" : "s"}`;
  btn.disabled = sessionBusy || approvedFileCount === 0;
}

document.getElementById("btn-commit").addEventListener("click", async () => {
  showCommitError(null);
  const box = document.getElementById("commit-message");
  const res = await fetch("/api/commit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: box.value.trim() }),
  });
  const data = await res.json();
  if (res.ok) {
    toast(`✓ committed ${data.commit} (${data.paths.length} file${data.paths.length === 1 ? "" : "s"})`);
    box.value = "";
  } else {
    showCommitError(data.detail);
  }
});

document.getElementById("btn-discard").addEventListener("click", async () => {
  showCommitError(null);
  if (!confirm("Discard all staged changes? The agent's work in the staging tree is lost.")) return;
  const res = await fetch("/api/discard", { method: "POST" });
  const data = await res.json();
  if (res.ok) {
    toast(`✓ discarded ${data.paths.length} file${data.paths.length === 1 ? "" : "s"}`);
    document.getElementById("commit-message").value = "";
  } else {
    showCommitError(data.detail);
  }
});

document.getElementById("prompt-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("prompt-input");
  const promptText = input.value.trim();
  if (!promptText) return;
  const continueCheckbox = document.getElementById("continue-session");
  const continueSession = continueCheckbox.checked;
  if (domainModeView === "design") {
    if (!continueSession) designDialogue = [];
    pendingDesignDialoguePrompt = promptText;
    renderDesignDialogue();
  }
  const body = { prompt: promptText, continue_session: continueSession, scope: domainModeView };
  const res = await fetch("/api/prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (res.ok) {
    input.value = "";
    continueCheckbox.checked = false;
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

document.querySelectorAll('#code-mode-toggle input[name="code-mode"]').forEach((input) => {
  input.addEventListener("change", (event) => {
    if (event.target.checked) setCodeDisplayMode(event.target.value);
  });
});

document.querySelectorAll('#domain-mode-toggle input[name="domain-mode"]').forEach((input) => {
  input.addEventListener("change", (event) => {
    if (event.target.checked) setDomainModeView(event.target.value);
  });
});

const POLL_INTERVAL_MS = 1500;

async function pollHashAndSession() {
  try {
    const res = await fetch("/api/hash");
    const data = await res.json();
    if (data.hash !== currentHash) loadGraph();
    const sessionRes = await fetch("/api/session");
    renderSessionState(await sessionRes.json());
  } catch {
    /* server briefly unreachable; keep polling */
  } finally {
    setTimeout(pollHashAndSession, POLL_INTERVAL_MS);
  }
}

setTimeout(pollHashAndSession, POLL_INTERVAL_MS);


loadGraph();
