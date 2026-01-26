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

    // Create force simulation with validated edges
    const simulation = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
      .force("link", d3.forceLink(validEdges)
        .id((d: any) => d.id)
        .distance(180)
      )
      .force("charge", d3.forceManyBody().strength(-600))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(70));

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
      .attr("stdDeviation", "3")
      .attr("result", "coloredBlur");
    
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Arrow marker for directed edges
    defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 35)
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
        .attr("refX", 35)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", color);
    });

    // Draw edges with arrows
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(validEdges)
      .enter()
      .append("line")
      .attr("class", (d) => d.is_circular ? "circular-edge" : "")
      .attr("stroke", (d) => getEdgeColor(d))
      .attr("stroke-width", (d) => d.is_circular ? 3 : 2)
      .attr("stroke-opacity", 0.8)
      .attr("stroke-dasharray", (d) => d.is_circular ? "5,5" : "none")
      .attr("marker-end", (d) => {
        const rel = d.relationship?.toLowerCase() || "related";
        if (d.is_circular) return "url(#arrowhead-circular)";
        if (RELATIONSHIP_COLORS[rel]) return `url(#arrowhead-${rel})`;
        return "url(#arrowhead)";
      });

    // Draw edge label backgrounds
    const linkLabelBgs = g.append("g")
      .attr("class", "link-label-bgs")
      .selectAll("rect")
      .data(validEdges)
      .enter()
      .append("rect")
      .attr("fill", (d) => getEdgeColor(d))
      .attr("rx", 3)
      .attr("ry", 3)
      .attr("opacity", 0.9);

    // Draw edge labels
    const linkLabels = g.append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(validEdges)
      .enter()
      .append("text")
      .attr("fill", "#ffffff")
      .attr("font-size", "9px")
      .attr("font-weight", "500")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .text((d) => formatRelationshipLabel(d));

    // Draw nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .enter()
      .append("g")
      .attr("cursor", "pointer")
      .call(d3.drag<SVGGElement, any>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended)
      )
      .on("click", (event, d) => {
        setSelectedNode(d as EntityNode);
      });

    // Node circles
    node.append("circle")
      .attr("r", (d: any) => d.is_root ? 30 : 25)
      .attr("fill", (d: any) => {
        if (d.is_root) return "#10b981"; // Green for root/audited company
        if (d.is_boilerplate || d.type === "boilerplate") return "#6b7280"; // Gray for boilerplate
        if (d.red_flags && d.red_flags.length > 0) return "#ef4444";
        if (d.type === "company") return "#3b82f6";
        if (d.type === "individual") return "#8b5cf6";
        return "#666666";
      })
      .attr("stroke", (d: any) => {
        if (d.is_root) return "#34d399"; // Bright green stroke for root
        if (d.is_boilerplate || d.type === "boilerplate") return "#9ca3af"; // Gray stroke for boilerplate
        if (d.red_flags && d.red_flags.length > 0) return "#ff3366";
        return "#00d4ff";
      })
      .attr("stroke-width", (d: any) => d.is_root ? 3 : 2)
      .attr("stroke-dasharray", (d: any) => (d.is_boilerplate || d.type === "boilerplate") ? "4,2" : "none")
      .attr("filter", "url(#glow)");

    // Node icons
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "white")
      .attr("font-size", (d: any) => d.is_root ? "16px" : "14px")
      .attr("font-weight", (d: any) => d.is_root ? "bold" : "normal")
      .text((d: any) => {
        if (d.is_root) return "A"; // A for Audited company
        if (d.is_boilerplate || d.type === "boilerplate") return "?";
        if (d.type === "company") return "B";
        if (d.type === "individual") return "P";
        return "?";
      });

    // Node labels
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "45px")
      .attr("fill", "#fafafa")
      .attr("font-size", "11px")
      .text((d: any) => d.name?.slice(0, 20) || d.id);

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      // Position label backgrounds
      linkLabelBgs
        .attr("x", (d: any) => {
          const label = formatRelationshipLabel(d);
          return (d.source.x + d.target.x) / 2 - (label.length * 3 + 6);
        })
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2 - 8)
        .attr("width", (d: any) => {
          const label = formatRelationshipLabel(d);
          return label.length * 6 + 12;
        })
        .attr("height", 16);

      linkLabels
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [nodes, validEdges, width, height]);

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
