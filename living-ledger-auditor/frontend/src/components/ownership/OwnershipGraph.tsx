"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";

interface EntityNode {
  id: string;
  name: string;
  type: "company" | "individual" | "unknown" | "boilerplate";
  jurisdiction?: string;
  red_flags?: string[];
  is_boilerplate?: boolean;
  is_root?: boolean;
  // Layout properties (assigned during rendering)
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  depth?: number;
}

interface OwnershipEdge {
  source: string;
  target: string;
  relationship: string;
  percentage?: number;
  is_circular?: boolean;
}

interface OwnershipGraphProps {
  nodes: EntityNode[];
  edges: OwnershipEdge[];
  width?: number;
  height?: number;
}

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

// Format relationship label for display
function formatRelationshipLabel(edge: OwnershipEdge): string {
  const rel = edge.relationship?.toLowerCase() || "related";
  
  if (rel === "owns" || rel === "beneficial_owner") {
    return edge.percentage ? `owns ${edge.percentage}%` : "owns";
  }
  if (rel === "parent_company") {
    return edge.percentage ? `parent ${edge.percentage}%` : "parent";
  }
  if (rel === "vendor") return "vendor";
  if (rel === "consultant") return "consultant";
  if (rel === "supplier") return "supplier";
  if (rel === "directs" || rel === "director") return "directs";
  
  return rel;
}

// Get edge color based on relationship
function getEdgeColor(edge: OwnershipEdge): string {
  if (edge.is_circular) return RELATIONSHIP_COLORS["circular"];
  const rel = edge.relationship?.toLowerCase() || "related";
  return RELATIONSHIP_COLORS[rel] || RELATIONSHIP_COLORS["related"];
}

// Build a tree structure from nodes and edges for D3 tree layout
interface TreeNode {
  id: string;
  name: string;
  data: EntityNode;
  children: TreeNode[];
}

function buildTreeStructure(nodes: EntityNode[], edges: OwnershipEdge[]): TreeNode | null {
  if (nodes.length === 0) return null;
  
  // Find root node
  const rootNode = nodes.find(n => n.is_root) || nodes[0];
  
  // Build adjacency list (directed from source to target)
  const children = new Map<string, Set<string>>();
  const edgeMap = new Map<string, OwnershipEdge>();
  
  for (const edge of edges) {
    const source = typeof edge.source === 'object' ? (edge.source as any).id : edge.source;
    const target = typeof edge.target === 'object' ? (edge.target as any).id : edge.target;
    
    if (!children.has(source)) children.set(source, new Set());
    children.get(source)!.add(target);
    edgeMap.set(`${source}->${target}`, edge);
  }
  
  // Build tree using BFS from root
  const visited = new Set<string>();
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  
  function buildNode(nodeId: string): TreeNode | null {
    if (visited.has(nodeId)) return null;
    visited.add(nodeId);
    
    const node = nodeMap.get(nodeId);
    if (!node) return null;
    
    const childIds = children.get(nodeId) || new Set();
    const childNodes: TreeNode[] = [];
    
    for (const childId of childIds) {
      const child = buildNode(childId);
      if (child) childNodes.push(child);
    }
    
    // Also check reverse edges (for ownership relationships where target owns source)
    for (const [key, edge] of edgeMap) {
      const target = typeof edge.target === 'object' ? (edge.target as any).id : edge.target;
      const source = typeof edge.source === 'object' ? (edge.source as any).id : edge.source;
      
      if (target === nodeId && !visited.has(source)) {
        const child = buildNode(source);
        if (child) childNodes.push(child);
      }
    }
    
    return {
      id: nodeId,
      name: node.name,
      data: node,
      children: childNodes
    };
  }
  
  return buildNode(rootNode.id);
}

export default function OwnershipGraph({ 
  nodes, 
  edges, 
  width = 800, 
  height = 500 
}: OwnershipGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);

  // Filter edges to only include those with valid node references
  const validEdges = useMemo(() => {
    const nodeIds = new Set(nodes.map(n => n.id));
    return edges.filter(e => {
      const sourceId = typeof e.source === 'object' ? (e.source as any).id : e.source;
      const targetId = typeof e.target === 'object' ? (e.target as any).id : e.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
  }, [nodes, edges]);

  // Create edge lookup for rendering
  const edgeLookup = useMemo(() => {
    const lookup = new Map<string, OwnershipEdge>();
    for (const edge of validEdges) {
      const source = typeof edge.source === 'object' ? (edge.source as any).id : edge.source;
      const target = typeof edge.target === 'object' ? (edge.target as any).id : edge.target;
      lookup.set(`${source}->${target}`, edge);
      lookup.set(`${target}->${source}`, edge); // Also store reverse for lookup
    }
    return lookup;
  }, [validEdges]);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Create container group with zoom
    const g = svg.append("g");

    // Setup zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Build tree structure
    const treeData = buildTreeStructure(nodes, validEdges);
    
    if (!treeData) return;

    // Create D3 hierarchy
    const root = d3.hierarchy(treeData);
    
    // Calculate tree dimensions based on node count
    const nodeCount = root.descendants().length;
    const treeWidth = Math.max(width - 100, nodeCount * 80);
    const treeHeight = Math.max(height - 100, root.height * 120);
    
    // Create tree layout - horizontal tree (root on left)
    const treeLayout = d3.tree<TreeNode>()
      .size([treeHeight, treeWidth])
      .separation((a, b) => (a.parent === b.parent ? 1.5 : 2));
    
    // Apply layout
    treeLayout(root);
    
    // Center the tree
    const offsetX = 80;
    const offsetY = (height - treeHeight) / 2;

    // Create gradient definitions
    const defs = svg.append("defs");
    
    // Glow filter
    const filter = defs.append("filter")
      .attr("id", "glow")
      .attr("x", "-50%")
      .attr("y", "-50%")
      .attr("width", "200%")
      .attr("height", "200%");
    
    filter.append("feGaussianBlur")
      .attr("stdDeviation", "2")
      .attr("result", "coloredBlur");
    
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Arrow marker for directed edges
    defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#666666");

    // Create colored arrow markers for each relationship type
    Object.entries(RELATIONSHIP_COLORS).forEach(([rel, color]) => {
      defs.append("marker")
        .attr("id", `arrowhead-${rel}`)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", color);
    });

    // Get all tree links
    const treeLinks = root.links();

    // Draw links (straight lines with elbow connectors for tree structure)
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("path")
      .data(treeLinks)
      .enter()
      .append("path")
      .attr("d", (d: any) => {
        // Use elbow connector for clean tree look
        const sourceX = d.source.y + offsetX;
        const sourceY = d.source.x + offsetY;
        const targetX = d.target.y + offsetX;
        const targetY = d.target.x + offsetY;
        const midX = (sourceX + targetX) / 2;
        
        return `M${sourceX},${sourceY} L${midX},${sourceY} L${midX},${targetY} L${targetX},${targetY}`;
      })
      .attr("stroke", (d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        return edge ? getEdgeColor(edge) : "#666666";
      })
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.8)
      .attr("fill", "none")
      .attr("marker-end", (d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        if (!edge) return "url(#arrowhead)";
        const rel = edge.relationship?.toLowerCase() || "related";
        if (edge.is_circular) return "url(#arrowhead-circular)";
        if (RELATIONSHIP_COLORS[rel]) return `url(#arrowhead-${rel})`;
        return "url(#arrowhead)";
      });

    // Draw edge labels at midpoint of each link
    const linkLabels = g.append("g")
      .attr("class", "link-labels")
      .selectAll("g")
      .data(treeLinks)
      .enter()
      .append("g")
      .attr("transform", (d: any) => {
        const sourceX = d.source.y + offsetX;
        const sourceY = d.source.x + offsetY;
        const targetX = d.target.y + offsetX;
        const targetY = d.target.x + offsetY;
        const midX = (sourceX + targetX) / 2;
        const midY = (sourceY + targetY) / 2;
        return `translate(${midX},${midY})`;
      });

    // Label background
    linkLabels.append("rect")
      .attr("fill", (d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        return edge ? getEdgeColor(edge) : "#666666";
      })
      .attr("rx", 3)
      .attr("ry", 3)
      .attr("x", (d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        const label = edge ? formatRelationshipLabel(edge) : "related";
        return -(label.length * 3 + 6);
      })
      .attr("y", -8)
      .attr("width", (d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        const label = edge ? formatRelationshipLabel(edge) : "related";
        return label.length * 6 + 12;
      })
      .attr("height", 16)
      .attr("opacity", 0.9);

    // Label text
    linkLabels.append("text")
      .attr("fill", "#ffffff")
      .attr("font-size", "9px")
      .attr("font-weight", "500")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .text((d: any) => {
        const edge = edgeLookup.get(`${d.source.data.id}->${d.target.data.id}`) ||
                     edgeLookup.get(`${d.target.data.id}->${d.source.data.id}`);
        return edge ? formatRelationshipLabel(edge) : "related";
      });

    // Draw nodes at tree positions
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(root.descendants())
      .enter()
      .append("g")
      .attr("transform", (d: any) => `translate(${d.y + offsetX},${d.x + offsetY})`)
      .attr("cursor", "pointer")
      .on("click", (event, d: any) => {
        setSelectedNode(d.data.data as EntityNode);
      });

    // Node circles
    node.append("circle")
      .attr("r", (d: any) => d.data.data.is_root ? 25 : 20)
      .attr("fill", (d: any) => {
        const nodeData = d.data.data;
        if (nodeData.is_root) return "#10b981";
        if (nodeData.is_boilerplate || nodeData.type === "boilerplate") return "#6b7280";
        if (nodeData.red_flags && nodeData.red_flags.length > 0) return "#ef4444";
        if (nodeData.type === "company") return "#3b82f6";
        if (nodeData.type === "individual") return "#8b5cf6";
        return "#666666";
      })
      .attr("stroke", (d: any) => {
        const nodeData = d.data.data;
        if (nodeData.is_root) return "#34d399";
        if (nodeData.is_boilerplate || nodeData.type === "boilerplate") return "#9ca3af";
        if (nodeData.red_flags && nodeData.red_flags.length > 0) return "#ff3366";
        return "#00d4ff";
      })
      .attr("stroke-width", (d: any) => d.data.data.is_root ? 3 : 2)
      .attr("stroke-dasharray", (d: any) => 
        (d.data.data.is_boilerplate || d.data.data.type === "boilerplate") ? "4,2" : "none"
      )
      .attr("filter", "url(#glow)");

    // Node icons
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "white")
      .attr("font-size", (d: any) => d.data.data.is_root ? "14px" : "12px")
      .attr("font-weight", (d: any) => d.data.data.is_root ? "bold" : "normal")
      .text((d: any) => {
        const nodeData = d.data.data;
        if (nodeData.is_root) return "A";
        if (nodeData.is_boilerplate || nodeData.type === "boilerplate") return "?";
        if (nodeData.type === "company") return "B";
        if (nodeData.type === "individual") return "P";
        return "?";
      });

    // Node labels (positioned to the side to avoid overlap)
    node.append("text")
      .attr("text-anchor", (d: any) => d.children ? "end" : "start")
      .attr("x", (d: any) => d.children ? -28 : 28)
      .attr("dy", "0.35em")
      .attr("fill", "#fafafa")
      .attr("font-size", "10px")
      .text((d: any) => {
        const name = d.data.name || d.data.id;
        return name.length > 18 ? name.slice(0, 18) + "..." : name;
      });

    // Initial zoom to fit content
    const bounds = g.node()?.getBBox();
    if (bounds) {
      const fullWidth = bounds.width + 100;
      const fullHeight = bounds.height + 100;
      const scale = Math.min(width / fullWidth, height / fullHeight, 1);
      const translateX = (width - fullWidth * scale) / 2 - bounds.x * scale + 50;
      const translateY = (height - fullHeight * scale) / 2 - bounds.y * scale + 50;
      
      svg.call(zoom.transform, d3.zoomIdentity.translate(translateX, translateY).scale(scale));
    }

  }, [nodes, validEdges, edgeLookup, width, height]);

  return (
    <div className="relative">
      <style>{`
        @keyframes pulse-circular {
          0%, 100% { stroke-opacity: 0.8; }
          50% { stroke-opacity: 0.4; }
        }
        .circular-edge {
          animation: pulse-circular 1.5s ease-in-out infinite;
        }
      `}</style>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-[#0a0a0a] rounded-lg border border-[#1f1f1f]"
      />
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[#111111]/90 backdrop-blur p-3 rounded border border-[#1f1f1f] text-xs max-w-[220px]">
        <div className="text-[#888] mb-2 font-medium">Entities</div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-[#10b981] border-2 border-[#34d399] flex-shrink-0" />
          <span className="truncate">Audited Company</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-[#3b82f6] flex-shrink-0" />
          <span className="truncate">Company</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-[#8b5cf6] flex-shrink-0" />
          <span className="truncate">Individual</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-[#ef4444] flex-shrink-0" />
          <span className="truncate">Red Flag</span>
        </div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-3 h-3 rounded-full bg-[#6b7280] border border-dashed border-[#9ca3af] flex-shrink-0" />
          <span className="truncate">Boilerplate</span>
        </div>
        
        <div className="text-[#888] mb-2 font-medium">Relationships</div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-0.5 bg-[#00d4ff] flex-shrink-0" />
          <span className="truncate">Owns</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-0.5 bg-[#22c55e] flex-shrink-0" />
          <span className="truncate">Vendor/Supplier</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-0.5 bg-[#a855f7] flex-shrink-0" />
          <span className="truncate">Director</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-0.5 bg-[#f97316] flex-shrink-0" />
          <span className="truncate">Parent Company</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 bg-[#ef4444] flex-shrink-0" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #ef4444 0, #ef4444 4px, transparent 4px, transparent 8px)' }} />
          <span className="truncate text-[#ef4444]">Circular Pattern</span>
        </div>
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bg-[#111111]/90 backdrop-blur p-4 rounded border border-[#1f1f1f] w-64 max-h-[300px] overflow-y-auto">
          <h4 className="font-semibold mb-2 break-words">{selectedNode.name}</h4>
          <p className="text-sm text-muted-foreground mb-1">
            Type: <span className="capitalize">{selectedNode.type}</span>
          </p>
          {(selectedNode.is_boilerplate || selectedNode.type === "boilerplate") && (
            <p className="text-sm text-[#9ca3af] mb-1 italic">
              Boilerplate/Template Company
            </p>
          )}
          {selectedNode.jurisdiction && (
            <p className="text-sm text-muted-foreground mb-1 break-words">
              Jurisdiction: {selectedNode.jurisdiction}
            </p>
          )}
          {selectedNode.red_flags && selectedNode.red_flags.length > 0 && (
            <div className="mt-2">
              <p className="text-sm text-[#ff3366] font-medium">Red Flags:</p>
              {selectedNode.red_flags.map((flag, i) => (
                <p key={i} className="text-xs text-muted-foreground break-words">- {flag}</p>
              ))}
            </div>
          )}
          <button
            onClick={() => setSelectedNode(null)}
            className="mt-2 text-xs text-[#00d4ff] hover:underline"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
