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
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
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

// Custom force to push nodes away from edges they're not connected to
function forceAvoidEdges(links: any[], nodeRadius: number) {
  let nodes: any[] = [];
  
  function force(alpha: number) {
    for (const node of nodes) {
      for (const link of links) {
        const source = link.source;
        const target = link.target;
        
        // Skip if this node is part of this edge
        if (node.id === source.id || node.id === target.id) continue;
        
        // Calculate distance from node to edge
        const dist = pointToSegmentDistance(
          node.x, node.y,
          source.x, source.y,
          target.x, target.y
        );
        
        // If too close, push the node away
        const minDist = nodeRadius + 15;
        if (dist < minDist && dist > 0) {
          // Find the nearest point on the line
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const lengthSq = dx * dx + dy * dy;
          
          if (lengthSq > 0) {
            let t = ((node.x - source.x) * dx + (node.y - source.y) * dy) / lengthSq;
            t = Math.max(0.1, Math.min(0.9, t));
            
            const nearestX = source.x + t * dx;
            const nearestY = source.y + t * dy;
            
            // Push perpendicular to the edge
            const pushX = node.x - nearestX;
            const pushY = node.y - nearestY;
            const pushDist = Math.sqrt(pushX * pushX + pushY * pushY);
            
            if (pushDist > 0) {
              const strength = alpha * (minDist - dist) / minDist * 2;
              node.vx += (pushX / pushDist) * strength * 20;
              node.vy += (pushY / pushDist) * strength * 20;
            }
          }
        }
      }
    }
  }
  
  force.initialize = function(_nodes: any[]) {
    nodes = _nodes;
  };
  
  return force;
}

export default function OwnershipGraph({ 
  nodes, 
  edges, 
  width = 600, 
  height = 400 
}: OwnershipGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);

  // Filter edges to only include those with valid node references
  const validEdges = useMemo(() => {
    const nodeIds = new Set(nodes.map(n => n.id));
    return edges.filter(e => {
      const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
      const targetId = typeof e.target === 'object' ? e.target.id : e.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
  }, [nodes, edges]);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const centerX = width / 2;
    const centerY = height / 2;
    const nodeRadius = 18;

    // Create container group with zoom
    const g = svg.append("g");

    // Setup zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Create node copies for simulation - spread them out initially
    const simNodes = nodes.map((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      const radius = n.is_root ? 0 : 150 + Math.random() * 100;
      return {
        ...n,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        fx: n.is_root ? centerX : null,
        fy: n.is_root ? centerY : null,
      };
    });

    // Create edge copies for simulation
    const simEdges = validEdges.map(e => ({
      ...e,
      source: typeof e.source === 'object' ? e.source.id : e.source,
      target: typeof e.target === 'object' ? e.target.id : e.target,
    }));

    // Create force simulation with strong separation
    const linkForce = d3.forceLink(simEdges as any)
      .id((d: any) => d.id)
      .distance(120)
      .strength(0.3);

    const simulation = d3.forceSimulation(simNodes as any)
      .force("link", linkForce)
      .force("charge", d3.forceManyBody()
        .strength(-500)
        .distanceMax(500))
      .force("center", d3.forceCenter(centerX, centerY))
      .force("collision", d3.forceCollide().radius(nodeRadius + 30).strength(1))
      .force("avoidEdges", forceAvoidEdges(simEdges, nodeRadius));

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

    // Draw edges
    const edgeGroup = g.append("g").attr("class", "edges");
    
    const links = edgeGroup.selectAll("line")
      .data(simEdges)
      .enter()
      .append("line")
      .attr("stroke", d => getEdgeColor(d as any))
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.7);

    // Edge labels group
    const labelGroup = g.append("g").attr("class", "edge-labels");
    
    const edgeLabels = labelGroup.selectAll("g")
      .data(simEdges)
      .enter()
      .append("g");

    // Label background
    edgeLabels.append("rect")
      .attr("fill", d => getEdgeColor(d as any))
      .attr("rx", 3)
      .attr("ry", 3)
      .attr("opacity", 0.9);

    // Label text
    edgeLabels.append("text")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("fill", "#ffffff")
      .attr("font-size", "8px")
      .attr("font-weight", "500")
      .text(d => formatLabel(d as any));

    // Size the label backgrounds based on text
    edgeLabels.each(function(d) {
      const g = d3.select(this);
      const text = g.select("text");
      const bbox = (text.node() as SVGTextElement)?.getBBox();
      if (bbox) {
        g.select("rect")
          .attr("x", -bbox.width / 2 - 4)
          .attr("y", -bbox.height / 2 - 2)
          .attr("width", bbox.width + 8)
          .attr("height", bbox.height + 4);
      }
    });

    // Draw nodes on top
    const nodeGroup = g.append("g").attr("class", "nodes");
    
    const nodeElements = nodeGroup.selectAll("g")
      .data(simNodes)
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
          if (!d.is_root) {
            d.fx = null;
            d.fy = null;
          }
        }))
      .on("click", (event, d) => {
        event.stopPropagation();
        setSelectedNode(d as EntityNode);
      });

    // Node circles
    nodeElements.append("circle")
      .attr("r", d => d.is_root ? 24 : nodeRadius)
      .attr("fill", d => {
        if (d.is_root) return "#10b981";
        if (d.is_boilerplate || d.type === "boilerplate") return "#6b7280";
        if (d.red_flags && d.red_flags.length > 0) return "#ef4444";
        if (d.type === "company") return "#3b82f6";
        if (d.type === "individual") return "#8b5cf6";
        return "#666666";
      })
      .attr("stroke", d => {
        if (d.is_root) return "#34d399";
        if (d.is_boilerplate || d.type === "boilerplate") return "#9ca3af";
        if (d.red_flags && d.red_flags.length > 0) return "#ff3366";
        return "#00d4ff";
      })
      .attr("stroke-width", d => d.is_root ? 3 : 2)
      .attr("filter", "url(#glow)");

    // Node icons
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

    // Node labels
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

    // Update positions on simulation tick
    simulation.on("tick", () => {
      // Update link positions
      links
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      // Update edge label positions (at midpoint)
      edgeLabels.attr("transform", (d: any) => {
        const midX = (d.source.x + d.target.x) / 2;
        const midY = (d.source.y + d.target.y) / 2;
        return `translate(${midX},${midY})`;
      });

      // Update node positions
      nodeElements.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    // Run simulation longer for better layout
    simulation.alpha(1).restart();
    
    // Let it run for 5 seconds then cool down
    setTimeout(() => {
      simulation.alphaTarget(0);
    }, 5000);

    // Initial zoom to fit
    svg.call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(0.8));

    // Cleanup
    return () => {
      simulation.stop();
    };

  }, [nodes, validEdges, width, height]);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-[#0a0a0a] rounded-lg border border-[#1f1f1f]"
      />
      
      {/* Compact Legend */}
      <div className="absolute bottom-2 left-2 bg-[#111111]/90 backdrop-blur p-2 rounded border border-[#1f1f1f] text-[10px]">
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

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="absolute top-2 right-2 bg-[#111111]/95 backdrop-blur p-3 rounded border border-[#1f1f1f] w-56 max-h-[200px] overflow-y-auto text-sm">
          <h4 className="font-semibold mb-1 break-words text-[#fafafa]">{selectedNode.name}</h4>
          <p className="text-xs text-muted-foreground">
            Type: <span className="capitalize">{selectedNode.type}</span>
          </p>
          {selectedNode.jurisdiction && (
            <p className="text-xs text-muted-foreground break-words">
              Jurisdiction: {selectedNode.jurisdiction}
            </p>
          )}
          {selectedNode.red_flags && selectedNode.red_flags.length > 0 && (
            <div className="mt-1">
              <p className="text-xs text-[#ff3366] font-medium">Red Flags:</p>
              {selectedNode.red_flags.map((flag, i) => (
                <p key={i} className="text-[10px] text-muted-foreground break-words">- {flag}</p>
              ))}
            </div>
          )}
          <button
            onClick={() => setSelectedNode(null)}
            className="mt-2 text-[10px] text-[#00d4ff] hover:underline"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
