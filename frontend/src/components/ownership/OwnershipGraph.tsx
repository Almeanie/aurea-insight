"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";
import {
  ZoomOut,
  Maximize2,
  Minimize2,
  Search,
  Loader2,
  CheckCircle2
} from 'lucide-react';

interface EntityNode {
  id: string;
  name: string;
  type: "company" | "individual" | "unknown" | "boilerplate";
  jurisdiction?: string;
  red_flags?: string[];
  is_boilerplate?: boolean;
  is_root?: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  // Additional data from registrar/APIs
  api_source?: string;
  registration_number?: string;
  status?: string;
  registered_address?: string;
  registration_date?: string;
  beneficial_owners?: any[];
  directors?: any[];
  lei?: string;
  ticker?: string;
  gemini_classification?: string;
  data_quality_score?: number;
  is_mock?: boolean;
}

interface OwnershipEdge {
  source: string | EntityNode;
  target: string | EntityNode;
  relationship: string;
  percentage?: number;
  is_circular?: boolean;
}

interface OwnershipGraphProps {
  nodes: EntityNode[];
  edges: OwnershipEdge[];
  width?: number;
  height?: number;
  isFullscreen?: boolean;
  onExpandClick?: () => void;
  onCloseFullscreen?: () => void;
  onNodeSelect?: (node: EntityNode | null) => void;
  selectedNode?: EntityNode | null;
  showInlineCard?: boolean; // If true, show card inside graph (default behavior)
}

// Export EntityNode type for parent components
export type { EntityNode };

// Color mapping for relationship types
const RELATIONSHIP_COLORS: Record<string, string> = {
  "owns": "#00d4ff",
  "beneficial_owner": "#00d4ff",
  "parent_company": "#f97316",
  "vendor": "#22c55e",
  "consultant": "#22c55e",
  "supplier": "#22c55e",
  "directs": "#a855f7",
  "director": "#a855f7",
  "circular": "#ef4444",
  "related": "#666666",
};

// Get edge color based on relationship
function getEdgeColor(edge: OwnershipEdge): string {
  if (edge.is_circular) return RELATIONSHIP_COLORS["circular"];
  const rel = edge.relationship?.toLowerCase() || "related";
  return RELATIONSHIP_COLORS[rel] || RELATIONSHIP_COLORS["related"];
}

// Format relationship label
function formatLabel(edge: OwnershipEdge): string {
  const rel = edge.relationship?.toLowerCase() || "related";
  if (rel === "owns" || rel === "beneficial_owner") {
    return edge.percentage ? `${edge.percentage}%` : "owns";
  }
  if (rel === "parent_company") return "parent";
  if (rel === "vendor") return "vendor";
  if (rel === "supplier") return "supplier";
  if (rel === "consultant") return "consult";
  if (rel === "directs" || rel === "director") return "director";
  return rel.slice(0, 6);
}

// Get node fill color
function getNodeFill(node: EntityNode): string {
  if (node.is_root) return "#10b981";
  if (node.is_boilerplate || node.type === "boilerplate") return "#6b7280";
  if (node.red_flags && node.red_flags.length > 0) return "#ef4444";
  if (node.type === "company") return "#3b82f6";
  if (node.type === "individual") return "#8b5cf6";
  return "#666666";
}

// Get node stroke color
function getNodeStroke(node: EntityNode): string {
  if (node.is_root) return "#34d399";
  if (node.is_boilerplate || node.type === "boilerplate") return "#9ca3af";
  if (node.red_flags && node.red_flags.length > 0) return "#ff3366";
  return "#00d4ff";
}

// Check if a point is too close to a line segment
function pointToSegmentDistance(
  px: number, py: number,
  x1: number, y1: number,
  x2: number, y2: number
): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const lengthSq = dx * dx + dy * dy;

  if (lengthSq === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);

  let t = ((px - x1) * dx + (py - y1) * dy) / lengthSq;
  t = Math.max(0, Math.min(1, t));

  const nearestX = x1 + t * dx;
  const nearestY = y1 + t * dy;

  return Math.sqrt((px - nearestX) ** 2 + (py - nearestY) ** 2);
}

// Check if two line segments intersect
function linesIntersect(
  x1: number, y1: number, x2: number, y2: number,
  x3: number, y3: number, x4: number, y4: number
): boolean {
  // Calculate direction vectors
  const d1x = x2 - x1, d1y = y2 - y1;
  const d2x = x4 - x3, d2y = y4 - y3;

  // Calculate cross product
  const cross = d1x * d2y - d1y * d2x;
  if (Math.abs(cross) < 0.001) return false; // Parallel lines

  const t = ((x3 - x1) * d2y - (y3 - y1) * d2x) / cross;
  const u = ((x3 - x1) * d1y - (y3 - y1) * d1x) / cross;

  // Check if intersection is within both segments (excluding endpoints)
  return t > 0.05 && t < 0.95 && u > 0.05 && u < 0.95;
}

// Get intersection point of two line segments
function getIntersectionPoint(
  x1: number, y1: number, x2: number, y2: number,
  x3: number, y3: number, x4: number, y4: number
): { x: number; y: number } | null {
  const d1x = x2 - x1, d1y = y2 - y1;
  const d2x = x4 - x3, d2y = y4 - y3;

  const cross = d1x * d2y - d1y * d2x;
  if (Math.abs(cross) < 0.001) return null;

  const t = ((x3 - x1) * d2y - (y3 - y1) * d2x) / cross;

  return { x: x1 + t * d1x, y: y1 + t * d1y };
}

// Force to reduce edge crossings
function forceUncrossEdges(links: any[]) {
  let nodes: any[] = [];

  function force(alpha: number) {
    // Find all edge crossings and push nodes to reduce them
    for (let i = 0; i < links.length; i++) {
      const link1 = links[i];
      const s1 = link1.source;
      const t1 = link1.target;
      if (!s1?.x || !t1?.x) continue;

      for (let j = i + 1; j < links.length; j++) {
        const link2 = links[j];
        const s2 = link2.source;
        const t2 = link2.target;
        if (!s2?.x || !t2?.x) continue;

        // Skip if links share a node
        if (s1.id === s2.id || s1.id === t2.id || t1.id === s2.id || t1.id === t2.id) continue;

        // Check if edges intersect
        if (linesIntersect(s1.x, s1.y, t1.x, t1.y, s2.x, s2.y, t2.x, t2.y)) {
          // Push nodes apart to uncross
          const intersection = getIntersectionPoint(s1.x, s1.y, t1.x, t1.y, s2.x, s2.y, t2.x, t2.y);
          if (!intersection) continue;

          const strength = alpha * 30;

          // Move nodes that are not fixed
          for (const node of [s1, t1, s2, t2]) {
            if (node.fx !== null && node.fy !== null) continue;

            // Calculate perpendicular push from intersection
            const dx = node.x - intersection.x;
            const dy = node.y - intersection.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist > 0 && dist < 150) {
              // Push away from intersection
              const pushStrength = strength * (1 - dist / 150);
              node.vx += (dx / dist) * pushStrength;
              node.vy += (dy / dist) * pushStrength;
            }
          }
        }
      }
    }
  }

  force.initialize = function (_nodes: any[]) {
    nodes = _nodes;
  };

  return force;
}

// Storage key for node positions
function getStorageKey(nodeIds: string[]): string {
  return `graph_positions_${nodeIds.sort().join('_').slice(0, 100)}`;
}

// Save node positions to localStorage
function saveNodePositions(nodes: any[], storageKey: string) {
  const positions: Record<string, { x: number; y: number; fx: number | null; fy: number | null }> = {};
  for (const node of nodes) {
    if (node.x !== undefined && node.y !== undefined) {
      positions[node.id] = {
        x: node.x,
        y: node.y,
        fx: node.fx,
        fy: node.fy
      };
    }
  }
  try {
    localStorage.setItem(storageKey, JSON.stringify(positions));
  } catch (e) {
    // Ignore storage errors
  }
}

// Load node positions from localStorage
function loadNodePositions(storageKey: string): Record<string, { x: number; y: number; fx: number | null; fy: number | null }> | null {
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    // Ignore storage errors
  }
  return null;
}

// Custom force to push nodes away from edges
function forceAvoidEdges(links: any[], nodeRadius: number) {
  let nodes: any[] = [];

  function force(alpha: number) {
    const minDist = nodeRadius + 40;

    for (const node of nodes) {
      if (node.fx !== null && node.fy !== null) continue;

      for (const link of links) {
        const source = link.source;
        const target = link.target;

        if (!source.x || !target.x) continue;
        if (node.id === source.id || node.id === target.id) continue;

        const dist = pointToSegmentDistance(
          node.x, node.y,
          source.x, source.y,
          target.x, target.y
        );

        if (dist < minDist && dist > 0) {
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const lengthSq = dx * dx + dy * dy;

          if (lengthSq > 0) {
            let t = ((node.x - source.x) * dx + (node.y - source.y) * dy) / lengthSq;
            t = Math.max(0.1, Math.min(0.9, t));

            const nearestX = source.x + t * dx;
            const nearestY = source.y + t * dy;

            let pushX = node.x - nearestX;
            let pushY = node.y - nearestY;
            const pushDist = Math.sqrt(pushX * pushX + pushY * pushY);

            if (pushDist > 0) {
              const strength = alpha * Math.pow((minDist - dist) / minDist, 2) * 50;
              node.vx += (pushX / pushDist) * strength;
              node.vy += (pushY / pushDist) * strength;
            } else {
              node.vx += (Math.random() - 0.5) * alpha * 30;
              node.vy += (Math.random() - 0.5) * alpha * 30;
            }
          }
        }
      }
    }
  }

  force.initialize = function (_nodes: any[]) {
    nodes = _nodes;
  };

  return force;
}

// Force to keep graph compact
function forceCompact(centerX: number, centerY: number, strength: number) {
  let nodes: any[] = [];

  function force(alpha: number) {
    for (const node of nodes) {
      if (node.fx !== null && node.fy !== null) continue;

      const dx = centerX - node.x;
      const dy = centerY - node.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist > 100) {
        const pull = alpha * strength * Math.min(dist / 500, 1);
        node.vx += dx * pull;
        node.vy += dy * pull;
      }
    }
  }

  force.initialize = function (_nodes: any[]) {
    nodes = _nodes;
  };

  return force;
}

export default function OwnershipGraph({
  nodes,
  edges,
  width = 600,
  height = 400,
  isFullscreen = false,
  onExpandClick,
  onCloseFullscreen,
  onNodeSelect,
  selectedNode: externalSelectedNode,
  showInlineCard = true
}: OwnershipGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width, height });
  // Use dimensions if available, otherwise fallback to props
  const graphWidth = dimensions.width || width;
  const graphHeight = dimensions.height || height;

  const svgRef = useRef<SVGSVGElement>(null);

  // Responsive resize observer
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null);
  const simulationRef = useRef<d3.Simulation<any, any> | null>(null);
  const simNodesRef = useRef<any[]>([]);
  const simEdgesRef = useRef<any[]>([]);
  const initializedRef = useRef(false);
  const [internalSelectedNode, setInternalSelectedNode] = useState<EntityNode | null>(null);

  // Use external selected node if provided, otherwise use internal state
  const selectedNode = externalSelectedNode !== undefined ? externalSelectedNode : internalSelectedNode;

  const setSelectedNode = (node: EntityNode | null) => {
    if (onNodeSelect) {
      onNodeSelect(node);
    } else {
      setInternalSelectedNode(node);
    }
  };

  // First pass: Filter out nodes with unknown/mock source (no real API data)
  const baseValidNodes = useMemo(() => {
    return nodes.filter(n => {
      // Keep root nodes always
      if (n.is_root) return true;
      // Filter out nodes with unknown/empty/mock api_source
      const source = n.api_source?.toLowerCase();
      if (!source || source === 'unknown' || source === 'unknown source' || source === 'mock_demo') {
        return false;
      }
      return true;
    });
  }, [nodes]);

  // Filter edges to only include valid ones (connected to base valid nodes)
  const validEdges = useMemo(() => {
    const nodeIds = new Set(baseValidNodes.map(n => n.id));
    return edges.filter(e => {
      const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
      const targetId = typeof e.target === 'object' ? e.target.id : e.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
  }, [baseValidNodes, edges]);

  // Second pass: Filter nodes to only include those that are connected (or root)
  const validNodes = useMemo(() => {
    // Get all node IDs that are part of an edge
    const connectedNodeIds = new Set<string>();
    validEdges.forEach(e => {
      const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
      const targetId = typeof e.target === 'object' ? e.target.id : e.target;
      connectedNodeIds.add(String(sourceId));
      connectedNodeIds.add(String(targetId));
    });

    return baseValidNodes.filter(n => n.is_root || connectedNodeIds.has(n.id));
  }, [baseValidNodes, validEdges]);

  // Track structure changes (only node IDs and edge connections)
  const structureKey = useMemo(() => {
    const nodeKey = validNodes.map(n => n.id).sort().join(',');
    const edgeKey = validEdges.map(e => {
      const s = typeof e.source === 'object' ? e.source.id : e.source;
      const t = typeof e.target === 'object' ? e.target.id : e.target;
      return `${s}-${t}`;
    }).sort().join(',');
    return `${nodeKey}|${edgeKey}`;
  }, [validNodes, validEdges]);

  // Update node colors when red_flags or other properties change (without re-rendering)
  useEffect(() => {
    if (!gRef.current || simNodesRef.current.length === 0) return;

    // Create a map of current node data
    const nodeDataMap = new Map(validNodes.map(n => [n.id, n]));

    // Update simulation nodes with new data
    simNodesRef.current.forEach(simNode => {
      const newData = nodeDataMap.get(simNode.id);
      if (newData) {
        simNode.red_flags = newData.red_flags;
        simNode.is_boilerplate = newData.is_boilerplate;
        simNode.jurisdiction = newData.jurisdiction;
      }
    });

    // Update visual appearance of nodes
    gRef.current.selectAll(".nodes g circle")
      .attr("fill", (d: any) => getNodeFill(d))
      .attr("stroke", (d: any) => getNodeStroke(d));

  }, [validNodes]); // Run when nodes change (including red_flags updates)

  // Handle Escape key to close selection
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedNode(null);
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [setSelectedNode]);

  // Initialize or update graph structure
  useEffect(() => {
    if (!svgRef.current || validNodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    const centerX = width / 2;
    const centerY = height / 2;
    const nodeRadius = 18;

    // Check if we need to rebuild or just update
    const currentNodeIds = new Set(simNodesRef.current.map(n => n.id));
    const newNodeIds = new Set(validNodes.map(n => n.id));

    // Find new nodes that don't exist yet
    const nodesToAdd = validNodes.filter(n => !currentNodeIds.has(n.id));
    const nodeIdsToRemove = [...currentNodeIds].filter(id => !newNodeIds.has(id));

    // If this is the first render or major structure change, rebuild everything
    if (!initializedRef.current || nodeIdsToRemove.length > simNodesRef.current.length / 2) {
      // Full rebuild
      svg.selectAll("*").remove();
      initializedRef.current = true;

      const g = svg.append("g");
      gRef.current = g;

      // Setup zoom
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.2, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        });
      svg.call(zoom);

      // Calculate storage key and try to load saved positions
      const storageKey = getStorageKey(validNodes.map(n => n.id));
      const savedPositions = loadNodePositions(storageKey);

      // Create simulation nodes with saved positions if available
      simNodesRef.current = validNodes.map((n, i) => {
        const saved = savedPositions?.[n.id];
        if (saved) {
          return {
            ...n,
            x: saved.x,
            y: saved.y,
            fx: saved.fx ?? (n.is_root ? centerX : null),
            fy: saved.fy ?? (n.is_root ? centerY : null),
          };
        }

        const angle = (i / validNodes.length) * 2 * Math.PI - Math.PI / 2;
        const radius = n.is_root ? 0 : 80 + (i % 3) * 40;
        return {
          ...n,
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
          fx: n.is_root ? centerX : null,
          fy: n.is_root ? centerY : null,
        };
      });

      // Create simulation edges
      simEdgesRef.current = validEdges.map(e => ({
        ...e,
        source: typeof e.source === 'object' ? e.source.id : e.source,
        target: typeof e.target === 'object' ? e.target.id : e.target,
      }));

      // Stop existing simulation
      if (simulationRef.current) {
        simulationRef.current.stop();
      }

      // Create new simulation
      const linkForce = d3.forceLink(simEdgesRef.current as any)
        .id((d: any) => d.id)
        .distance(120)
        .strength(0.5);

      const simulation = d3.forceSimulation(simNodesRef.current as any)
        .force("link", linkForce)
        .force("charge", d3.forceManyBody().strength(-400).distanceMax(400))
        .force("collision", d3.forceCollide().radius(nodeRadius + 35).strength(1))
        .force("avoidEdges", forceAvoidEdges(simEdgesRef.current, nodeRadius))
        .force("uncrossEdges", forceUncrossEdges(simEdgesRef.current))
        .force("compact", forceCompact(centerX, centerY, 0.015))
        .force("center", d3.forceCenter(graphWidth / 2, graphHeight / 2))
        .velocityDecay(0.3);

      simulationRef.current = simulation;

      // Create defs
      const defs = svg.append("defs");
      const filter = defs.append("filter")
        .attr("id", "glow")
        .attr("x", "-50%").attr("y", "-50%")
        .attr("width", "200%").attr("height", "200%");
      filter.append("feGaussianBlur").attr("stdDeviation", "2").attr("result", "coloredBlur");
      const feMerge = filter.append("feMerge");
      feMerge.append("feMergeNode").attr("in", "coloredBlur");
      feMerge.append("feMergeNode").attr("in", "SourceGraphic");

      // Draw edges - wider hitbox for hover
      const edgeGroup = g.append("g").attr("class", "edges");

      // Invisible wider lines for easier hover detection
      const linkHitboxes = edgeGroup.selectAll(".edge-hitbox")
        .data(simEdgesRef.current)
        .enter()
        .append("line")
        .attr("class", "edge-hitbox")
        .attr("stroke", "transparent")
        .attr("stroke-width", 15)
        .attr("cursor", "pointer");

      // Visible edge lines
      const links = edgeGroup.selectAll(".edge-line")
        .data(simEdgesRef.current)
        .enter()
        .append("line")
        .attr("class", "edge-line")
        .attr("stroke", d => getEdgeColor(d as any))
        .attr("stroke-width", 2)
        .attr("stroke-opacity", 0.7)
        .attr("pointer-events", "none");

      // Edge labels - hidden by default, shown on hover
      const labelGroup = g.append("g").attr("class", "edge-labels");
      const edgeLabels = labelGroup.selectAll("g")
        .data(simEdgesRef.current)
        .enter()
        .append("g")
        .attr("opacity", 0)
        .attr("pointer-events", "none");

      edgeLabels.append("rect")
        .attr("fill", d => getEdgeColor(d as any))
        .attr("rx", 3).attr("ry", 3);

      edgeLabels.append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "9px")
        .attr("font-weight", "600")
        .text(d => formatLabel(d as any));

      edgeLabels.each(function () {
        const grp = d3.select(this);
        const text = grp.select("text");
        const bbox = (text.node() as SVGTextElement)?.getBBox();
        if (bbox) {
          grp.select("rect")
            .attr("x", -bbox.width / 2 - 5)
            .attr("y", -bbox.height / 2 - 3)
            .attr("width", bbox.width + 10)
            .attr("height", bbox.height + 6);
        }
      });

      // Add hover effects to show/hide labels
      linkHitboxes
        .on("mouseenter", function (event, d: any) {
          // Find the matching label and show it
          edgeLabels.filter((ld: any) => {
            const ls = typeof ld.source === 'object' ? ld.source.id : ld.source;
            const lt = typeof ld.target === 'object' ? ld.target.id : ld.target;
            const ds = typeof d.source === 'object' ? d.source.id : d.source;
            const dt = typeof d.target === 'object' ? d.target.id : d.target;
            return ls === ds && lt === dt;
          })
            .transition()
            .duration(150)
            .attr("opacity", 1);

          // Highlight the edge
          links.filter((ld: any) => {
            const ls = typeof ld.source === 'object' ? ld.source.id : ld.source;
            const lt = typeof ld.target === 'object' ? ld.target.id : ld.target;
            const ds = typeof d.source === 'object' ? d.source.id : d.source;
            const dt = typeof d.target === 'object' ? d.target.id : d.target;
            return ls === ds && lt === dt;
          })
            .attr("stroke-width", 3)
            .attr("stroke-opacity", 1);
        })
        .on("mouseleave", function (event, d: any) {
          // Hide all labels
          edgeLabels
            .transition()
            .duration(300)
            .attr("opacity", 0);

          // Reset edge style
          links
            .attr("stroke-width", 2)
            .attr("stroke-opacity", 0.7);
        });

      // Draw nodes
      const nodeGroup = g.append("g").attr("class", "nodes");
      const nodeElements = nodeGroup.selectAll("g")
        .data(simNodesRef.current)
        .enter()
        .append("g")
        .attr("cursor", "pointer")
        .call(d3.drag<any, any>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = d.x;
            d.fy = d.y;
            // Save node positions to localStorage after drag
            saveNodePositions(simNodesRef.current, storageKey);
          }))
        .on("click", (event, d) => {
          event.stopPropagation();
          setSelectedNode(d as EntityNode);
        });

      nodeElements.append("circle")
        .attr("r", d => d.is_root ? 24 : nodeRadius)
        .attr("fill", d => getNodeFill(d))
        .attr("stroke", d => getNodeStroke(d))
        .attr("stroke-width", d => d.is_root ? 3 : 2)
        .attr("filter", "url(#glow)");

      nodeElements.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("fill", "white")
        .attr("font-size", d => d.is_root ? "12px" : "10px")
        .attr("font-weight", d => d.is_root ? "bold" : "normal")
        .attr("pointer-events", "none")
        .text(d => {
          if (d.is_root) return "A";
          if (d.is_boilerplate || d.type === "boilerplate") return "?";
          if (d.type === "company") return "B";
          if (d.type === "individual") return "P";
          return "?";
        });

      nodeElements.append("text")
        .attr("class", "node-label")
        .attr("text-anchor", "middle")
        .attr("y", d => (d.is_root ? 24 : nodeRadius) + 12)
        .attr("fill", "#fafafa")
        .attr("font-size", "9px")
        .attr("pointer-events", "none")
        .text(d => {
          const name = d.name || d.id;
          return name.length > 14 ? name.slice(0, 14) + "..." : name;
        });

      // Tick function
      simulation.on("tick", () => {
        // Update visible lines
        links
          .attr("x1", (d: any) => d.source.x)
          .attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x)
          .attr("y2", (d: any) => d.target.y);

        // Update hitbox lines
        linkHitboxes
          .attr("x1", (d: any) => d.source.x)
          .attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x)
          .attr("y2", (d: any) => d.target.y);

        edgeLabels.attr("transform", (d: any) => {
          const midX = (d.source.x + d.target.x) / 2;
          const midY = (d.source.y + d.target.y) / 2;
          return `translate(${midX},${midY})`;
        });

        nodeElements.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
      });

      simulation.alpha(0.5).restart();

      // Auto zoom to fit
      setTimeout(() => {
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        simNodesRef.current.forEach(n => {
          if (n.x < minX) minX = n.x;
          if (n.x > maxX) maxX = n.x;
          if (n.y < minY) minY = n.y;
          if (n.y > maxY) maxY = n.y;
        });

        const graphWidth = maxX - minX + 100;
        const graphHeight = maxY - minY + 100;
        const scale = Math.min(width / graphWidth, height / graphHeight, 1) * 0.9;
        const translateX = width / 2 - (minX + maxX) / 2 * scale;
        const translateY = height / 2 - (minY + maxY) / 2 * scale;

        svg.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(translateX, translateY).scale(scale)
        );
      }, 1000);

    } else if (nodesToAdd.length > 0) {
      // Incremental update - add new nodes without resetting existing positions
      const simulation = simulationRef.current;
      if (!simulation || !gRef.current) return;

      // Calculate storage key for incremental updates
      const incrementalStorageKey = getStorageKey(validNodes.map(n => n.id));

      // Add new nodes to simulation
      nodesToAdd.forEach((n, i) => {
        // Position new nodes near related nodes or at edge of existing cluster
        let x = centerX + (Math.random() - 0.5) * 100;
        let y = centerY + (Math.random() - 0.5) * 100;

        // Try to position near a connected node
        const connectedEdge = validEdges.find(e => {
          const s = typeof e.source === 'object' ? e.source.id : e.source;
          const t = typeof e.target === 'object' ? e.target.id : e.target;
          return s === n.id || t === n.id;
        });

        if (connectedEdge) {
          const connectedId = typeof connectedEdge.source === 'object'
            ? connectedEdge.source.id
            : connectedEdge.source;
          const otherId = connectedId === n.id
            ? (typeof connectedEdge.target === 'object' ? connectedEdge.target.id : connectedEdge.target)
            : connectedId;
          const connectedNode = simNodesRef.current.find(sn => sn.id === otherId);
          if (connectedNode) {
            const angle = Math.random() * 2 * Math.PI;
            x = connectedNode.x + 80 * Math.cos(angle);
            y = connectedNode.y + 80 * Math.sin(angle);
          }
        }

        simNodesRef.current.push({
          ...n,
          x,
          y,
          fx: n.is_root ? centerX : null,
          fy: n.is_root ? centerY : null,
        });
      });

      // Add new edges
      const currentEdgeKeys = new Set(simEdgesRef.current.map((e: any) => {
        const s = typeof e.source === 'object' ? e.source.id : e.source;
        const t = typeof e.target === 'object' ? e.target.id : e.target;
        return `${s}-${t}`;
      }));

      validEdges.forEach(e => {
        const s = typeof e.source === 'object' ? e.source.id : e.source;
        const t = typeof e.target === 'object' ? e.target.id : e.target;
        const key = `${s}-${t}`;
        if (!currentEdgeKeys.has(key)) {
          simEdgesRef.current.push({
            ...e,
            source: s,
            target: t,
          });
        }
      });

      // Update simulation with new data
      simulation.nodes(simNodesRef.current);
      (simulation.force("link") as d3.ForceLink<any, any>).links(simEdgesRef.current);
      simulation.force("avoidEdges", forceAvoidEdges(simEdgesRef.current, nodeRadius));
      simulation.force("uncrossEdges", forceUncrossEdges(simEdgesRef.current));

      // Rebuild visual elements
      const g = gRef.current;

      // Update edges - clear all and rebuild with hitboxes
      const edgeGroup = g.select(".edges");
      edgeGroup.selectAll("*").remove();

      // Invisible wider lines for easier hover detection
      const linkHitboxes = edgeGroup.selectAll(".edge-hitbox")
        .data(simEdgesRef.current)
        .enter()
        .append("line")
        .attr("class", "edge-hitbox")
        .attr("stroke", "transparent")
        .attr("stroke-width", 15)
        .attr("cursor", "pointer");

      // Visible edge lines
      const links = edgeGroup.selectAll(".edge-line")
        .data(simEdgesRef.current)
        .enter()
        .append("line")
        .attr("class", "edge-line")
        .attr("stroke", d => getEdgeColor(d as any))
        .attr("stroke-width", 2)
        .attr("stroke-opacity", 0.7)
        .attr("pointer-events", "none");

      // Update edge labels - hidden by default
      const labelGroup = g.select(".edge-labels");
      labelGroup.selectAll("g").remove();
      const edgeLabels = labelGroup.selectAll("g")
        .data(simEdgesRef.current)
        .enter()
        .append("g")
        .attr("opacity", 0)
        .attr("pointer-events", "none");

      edgeLabels.append("rect")
        .attr("fill", d => getEdgeColor(d as any))
        .attr("rx", 3).attr("ry", 3);

      edgeLabels.append("text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "9px")
        .attr("font-weight", "600")
        .text(d => formatLabel(d as any));

      edgeLabels.each(function () {
        const grp = d3.select(this);
        const text = grp.select("text");
        const bbox = (text.node() as SVGTextElement)?.getBBox();
        if (bbox) {
          grp.select("rect")
            .attr("x", -bbox.width / 2 - 5)
            .attr("y", -bbox.height / 2 - 3)
            .attr("width", bbox.width + 10)
            .attr("height", bbox.height + 6);
        }
      });

      // Add hover effects to show/hide labels
      linkHitboxes
        .on("mouseenter", function (event, d: any) {
          edgeLabels.filter((ld: any) => {
            const ls = typeof ld.source === 'object' ? ld.source.id : ld.source;
            const lt = typeof ld.target === 'object' ? ld.target.id : ld.target;
            const ds = typeof d.source === 'object' ? d.source.id : d.source;
            const dt = typeof d.target === 'object' ? d.target.id : d.target;
            return ls === ds && lt === dt;
          })
            .transition()
            .duration(150)
            .attr("opacity", 1);

          links.filter((ld: any) => {
            const ls = typeof ld.source === 'object' ? ld.source.id : ld.source;
            const lt = typeof ld.target === 'object' ? ld.target.id : ld.target;
            const ds = typeof d.source === 'object' ? d.source.id : d.source;
            const dt = typeof d.target === 'object' ? d.target.id : d.target;
            return ls === ds && lt === dt;
          })
            .attr("stroke-width", 3)
            .attr("stroke-opacity", 1);
        })
        .on("mouseleave", function () {
          edgeLabels
            .transition()
            .duration(300)
            .attr("opacity", 0);

          links
            .attr("stroke-width", 2)
            .attr("stroke-opacity", 0.7);
        });

      // Update nodes
      const nodeGroup = g.select(".nodes");
      nodeGroup.selectAll("g").remove();
      const nodeElements = nodeGroup.selectAll("g")
        .data(simNodesRef.current)
        .enter()
        .append("g")
        .attr("cursor", "pointer")
        .call(d3.drag<any, any>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = d.x;
            d.fy = d.y;
            // Save node positions to localStorage after drag
            saveNodePositions(simNodesRef.current, incrementalStorageKey);
          }))
        .on("click", (event, d) => {
          event.stopPropagation();
          setSelectedNode(d as EntityNode);
        });

      nodeElements.append("circle")
        .attr("r", d => d.is_root ? 24 : nodeRadius)
        .attr("fill", d => getNodeFill(d))
        .attr("stroke", d => getNodeStroke(d))
        .attr("stroke-width", d => d.is_root ? 3 : 2)
        .attr("filter", "url(#glow)");

      nodeElements.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("fill", "white")
        .attr("font-size", d => d.is_root ? "12px" : "10px")
        .attr("font-weight", d => d.is_root ? "bold" : "normal")
        .attr("pointer-events", "none")
        .text(d => {
          if (d.is_root) return "A";
          if (d.is_boilerplate || d.type === "boilerplate") return "?";
          if (d.type === "company") return "B";
          if (d.type === "individual") return "P";
          return "?";
        });

      nodeElements.append("text")
        .attr("text-anchor", "middle")
        .attr("y", d => (d.is_root ? 24 : nodeRadius) + 12)
        .attr("fill", "#fafafa")
        .attr("font-size", "9px")
        .attr("pointer-events", "none")
        .text(d => {
          const name = d.name || d.id;
          return name.length > 14 ? name.slice(0, 14) + "..." : name;
        });

      // Update tick
      simulation.on("tick", () => {
        g.select(".edges").selectAll("line")
          .attr("x1", (d: any) => d.source.x)
          .attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x)
          .attr("y2", (d: any) => d.target.y);

        g.select(".edge-labels").selectAll("g").attr("transform", (d: any) => {
          const midX = (d.source.x + d.target.x) / 2;
          const midY = (d.source.y + d.target.y) / 2;
          return `translate(${midX},${midY})`;
        });

        nodeElements.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
      });

      // Gentle restart for new nodes
      simulation.alpha(0.3).restart();
    }

    return () => {
      // Don't stop simulation on cleanup - let it continue
    };

  }, [structureKey, width, height]); // Only run when structure changes

  return (
    <div ref={containerRef} className="relative w-full h-full">
      {/* Expand/Close button */}
      {!isFullscreen && onExpandClick && (
        <button
          onClick={onExpandClick}
          className="absolute top-2 right-2 z-10 bg-[#111111]/90 backdrop-blur p-2 rounded border border-[#1f1f1f] hover:border-[#00d4ff] hover:bg-[#1a1a1a] transition-colors"
          title="Expand to fullscreen"
        >
          <svg className="w-4 h-4 text-[#00d4ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      )}

      {isFullscreen && onCloseFullscreen && (
        <button
          onClick={onCloseFullscreen}
          className="absolute top-4 right-4 z-10 bg-[#111111]/90 backdrop-blur px-4 py-2 rounded border border-[#1f1f1f] hover:border-[#ff3366] hover:bg-[#1a1a1a] transition-colors flex items-center gap-2"
          title="Close fullscreen"
        >
          <svg className="w-4 h-4 text-[#ff3366]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="text-sm text-[#fafafa]">Close</span>
        </button>
      )}

      <svg
        ref={svgRef}
        width={graphWidth}
        height={graphHeight}
        className={`bg-[#0a0a0a] ${isFullscreen ? 'rounded-none' : 'rounded-lg border border-[#1f1f1f]'}`}
      />

      {/* Compact Legend */}
      <div className={`absolute ${isFullscreen ? 'bottom-4 left-4' : 'bottom-2 left-2'} bg-[#111111]/90 backdrop-blur p-2 rounded border border-[#1f1f1f] text-[10px]`}>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#10b981]" />
            <span>Audited</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#3b82f6]" />
            <span>Company</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#8b5cf6]" />
            <span>Individual</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#ef4444]" />
            <span>Red Flag</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 pt-1 border-t border-[#1f1f1f]">
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-[#00d4ff]" />
            <span>Owns</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-[#22c55e]" />
            <span>Vendor</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-[#a855f7]" />
            <span>Director</span>
          </div>
        </div>
      </div>

      {/* Selected Node Info - Inline Modal (Centered) */}
      {showInlineCard && selectedNode && (
        <>
          {/* Backdrop for click-outside */}
          <div
            className="absolute inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
            onClick={() => setSelectedNode(null)}
          />
          <div className={`absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-[#111111]/95 backdrop-blur p-4 rounded-lg border border-[#1f1f1f] w-80 shadow-2xl ${isFullscreen ? 'max-h-[80vh]' : 'max-h-[350px]'} overflow-y-auto text-sm z-50`} onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold wrap-break-word text-[#fafafa] flex-1 pr-2">{selectedNode.name}</h4>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-[10px] text-[#666] hover:text-[#00d4ff] shrink-0"
              >
                X
              </button>
            </div>

            {/* Data Source Badge */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className={`text-[10px] px-2 py-0.5 rounded ${selectedNode.api_source === 'mock_demo' ? 'bg-[#666] text-white' :
                selectedNode.api_source === 'opencorporates' ? 'bg-[#22c55e] text-white' :
                  selectedNode.api_source === 'sec_edgar' ? 'bg-[#3b82f6] text-white' :
                    selectedNode.api_source === 'uk_companies_house' ? 'bg-[#8b5cf6] text-white' :
                      selectedNode.api_source === 'gleif' ? 'bg-[#f97316] text-white' :
                        'bg-[#444] text-white'
                }`}>
                {selectedNode.api_source || 'Unknown Source'}
              </span>


              {selectedNode.is_mock && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#444] text-[#888]">Demo Data</span>
              )}
              {selectedNode.is_root && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#10b981] text-white">Audited</span>
              )}
            </div>

            {/* Basic Info */}
            <div className="space-y-1 text-xs border-t border-[#1f1f1f] pt-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type:</span>
                <span className="capitalize text-[#fafafa]">{selectedNode.type}</span>
              </div>
              {selectedNode.jurisdiction && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Jurisdiction:</span>
                  <span className="text-[#fafafa]">{selectedNode.jurisdiction}</span>
                </div>
              )}
              {selectedNode.status && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={`${selectedNode.status === 'active' ? 'text-[#22c55e]' : 'text-[#ff6b35]'}`}>
                    {selectedNode.status}
                  </span>
                </div>
              )}
              {selectedNode.registration_number && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Reg. No:</span>
                  <span className="text-[#fafafa] font-mono text-[10px]">{selectedNode.registration_number}</span>
                </div>
              )}
              {selectedNode.registration_date && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Reg. Date:</span>
                  <span className="text-[#fafafa]">{selectedNode.registration_date}</span>
                </div>
              )}
              {selectedNode.lei && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">LEI:</span>
                  <span className="text-[#fafafa] font-mono text-[10px]">{selectedNode.lei.slice(0, 10)}...</span>
                </div>
              )}
              {selectedNode.ticker && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Ticker:</span>
                  <span className="text-[#00d4ff] font-bold">{selectedNode.ticker}</span>
                </div>
              )}
            </div>

            {/* Gemini Classification */}
            {selectedNode.gemini_classification && (
              <div className="mt-2 pt-2 border-t border-[#1f1f1f]">
                <div className="text-[10px] text-muted-foreground mb-1">AI Classification:</div>
                <div className="text-xs text-[#a855f7] capitalize">{selectedNode.gemini_classification.replace(/_/g, ' ')}</div>
                {selectedNode.data_quality_score !== undefined && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-muted-foreground">Data Quality:</span>
                    <div className="flex-1 bg-[#1f1f1f] rounded-full h-1.5">
                      <div
                        className="bg-[#00d4ff] h-1.5 rounded-full"
                        style={{ width: `${selectedNode.data_quality_score * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#fafafa]">{Math.round(selectedNode.data_quality_score * 100)}%</span>
                  </div>
                )}
              </div>
            )}

            {/* Red Flags */}
            {selectedNode.red_flags && selectedNode.red_flags.length > 0 && (
              <div className="mt-2 pt-2 border-t border-[#1f1f1f]">
                <div className="text-[10px] text-[#ff3366] font-medium mb-1">
                  Red Flags ({selectedNode.red_flags.length}):
                </div>
                <div className="space-y-1">
                  {selectedNode.red_flags.map((flag, i) => (
                    <div key={i} className="text-[10px] text-muted-foreground bg-[#1a0a0a] p-1.5 rounded border border-[#ff3366]/20">
                      {flag}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Registered Address */}
            {selectedNode.registered_address && (
              <div className="mt-2 pt-2 border-t border-[#1f1f1f]">
                <div className="text-[10px] text-muted-foreground mb-1">Registered Address:</div>
                <div className="text-[10px] text-[#fafafa]">{selectedNode.registered_address}</div>
              </div>
            )}

            {/* Directors */}
            {selectedNode.directors && selectedNode.directors.length > 0 && (
              <div className="mt-2 pt-2 border-t border-[#1f1f1f]">
                <div className="text-[10px] text-muted-foreground mb-1">
                  Directors ({selectedNode.directors.length}):
                </div>
                <div className="space-y-1">
                  {selectedNode.directors.slice(0, 3).map((dir: any, i: number) => (
                    <div key={i} className="text-[10px] text-[#fafafa] flex justify-between">
                      <span>{dir.name}</span>
                      {dir.role && <span className="text-muted-foreground">{dir.role}</span>}
                    </div>
                  ))}
                  {selectedNode.directors.length > 3 && (
                    <div className="text-[10px] text-muted-foreground">+{selectedNode.directors.length - 3} more</div>
                  )}
                </div>
              </div>
            )}

            {/* Beneficial Owners */}
            {selectedNode.beneficial_owners && selectedNode.beneficial_owners.length > 0 && (
              <div className="mt-2 pt-2 border-t border-[#1f1f1f]">
                <div className="text-[10px] text-muted-foreground mb-1">
                  Beneficial Owners ({selectedNode.beneficial_owners.length}):
                </div>
                <div className="space-y-1">
                  {selectedNode.beneficial_owners.slice(0, 3).map((owner: any, i: number) => (
                    <div key={i} className="text-[10px] text-[#fafafa] flex justify-between">
                      <span>{owner.name}</span>
                      {owner.ownership_percentage && (
                        <span className="text-[#00d4ff]">{owner.ownership_percentage}%</span>
                      )}
                    </div>
                  ))}
                  {selectedNode.beneficial_owners.length > 3 && (
                    <div className="text-[10px] text-muted-foreground">+{selectedNode.beneficial_owners.length - 3} more</div>
                  )}
                </div>
              </div>
            )}


          </div>
        </>
      )}
    </div>
  );
}
