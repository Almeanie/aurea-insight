"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface EntityNode {
  id: string;
  name: string;
  type: "company" | "individual" | "unknown" | "boilerplate";
  jurisdiction?: string;
  red_flags?: string[];
  is_boilerplate?: boolean;
}

interface OwnershipEdge {
  source: string;
  target: string;
  relationship: string;
  percentage?: number;
}

interface OwnershipGraphProps {
  nodes: EntityNode[];
  edges: OwnershipEdge[];
  width?: number;
  height?: number;
}

export default function OwnershipGraph({ 
  nodes, 
  edges, 
  width = 800, 
  height = 500 
}: OwnershipGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);

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

    // Create force simulation
    const simulation = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
      .force("link", d3.forceLink(edges)
        .id((d: any) => d.id)
        .distance(150)
      )
      .force("charge", d3.forceManyBody().strength(-500))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(60));

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

    // Draw edges
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(edges)
      .enter()
      .append("line")
      .attr("stroke", (d) => d.relationship === "owns" ? "#00d4ff" : "#666666")
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.6);

    // Draw edge labels
    const linkLabels = g.append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(edges)
      .enter()
      .append("text")
      .attr("fill", "#666666")
      .attr("font-size", "10px")
      .attr("text-anchor", "middle")
      .text((d) => d.percentage ? `${d.percentage}%` : d.relationship);

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
      .attr("r", 25)
      .attr("fill", (d: any) => {
        if (d.is_boilerplate || d.type === "boilerplate") return "#6b7280"; // Gray for boilerplate
        if (d.red_flags && d.red_flags.length > 0) return "#ef4444";
        if (d.type === "company") return "#3b82f6";
        if (d.type === "individual") return "#8b5cf6";
        return "#666666";
      })
      .attr("stroke", (d: any) => {
        if (d.is_boilerplate || d.type === "boilerplate") return "#9ca3af"; // Gray stroke for boilerplate
        if (d.red_flags && d.red_flags.length > 0) return "#ff3366";
        return "#00d4ff";
      })
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", (d: any) => (d.is_boilerplate || d.type === "boilerplate") ? "4,2" : "none")
      .attr("filter", "url(#glow)");

    // Node icons
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("fill", "white")
      .attr("font-size", "14px")
      .text((d: any) => {
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
  }, [nodes, edges, width, height]);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-[#0a0a0a] rounded-lg border border-[#1f1f1f]"
      />
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[#111111]/90 backdrop-blur p-3 rounded border border-[#1f1f1f] text-xs max-w-[200px]">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 rounded-full bg-[#3b82f6] flex-shrink-0" />
          <span className="truncate">Company</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 rounded-full bg-[#8b5cf6] flex-shrink-0" />
          <span className="truncate">Individual</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 rounded-full bg-[#ef4444] flex-shrink-0" />
          <span className="truncate">Red Flag</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#6b7280] border border-dashed border-[#9ca3af] flex-shrink-0" />
          <span className="truncate">Boilerplate</span>
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
