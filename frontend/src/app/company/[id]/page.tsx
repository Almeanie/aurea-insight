"use client";

import { use, useState, useEffect, useRef, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import OwnershipGraph, { EntityNode } from "@/components/ownership/OwnershipGraph";
import FindingDetailDialog from "@/components/audit/FindingDetailDialog";
import GeminiInteractionDialog from "@/components/audit/GeminiInteractionDialog";
import ReasoningStepDialog from "@/components/audit/ReasoningStepDialog";
import AJEDetailCard from "@/components/audit/AJEDetailCard";
import {
  Shield,
  Play,
  FileText,
  Network,
  MessageSquare,
  AlertTriangle,
  TrendingUp,
  ChevronLeft,
  Download,
  CheckCircle,
  Clock,
  Brain,
  Hash,
  Send,
  Loader2,
  Search,
  Eye,
  Code,
  Lock
} from "lucide-react";
import Link from "next/link";
import QuotaExceededModal from "@/components/ui/QuotaExceededModal";
import { AuditProgress } from "@/components/ui/progress";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function CompanyPage({ params }: PageProps) {
  const { id } = use(params);
  const [company, setCompany] = useState<any>(null);
  const [coa, setCoa] = useState<any>(null);
  const [gl, setGl] = useState<any>(null);
  const [tb, setTb] = useState<any>(null);
  const [auditResults, setAuditResults] = useState<any>(null);
  const [auditTrail, setAuditTrail] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuditing, setIsAuditing] = useState(false);
  const [liveReasoningSteps, setLiveReasoningSteps] = useState<string[]>([]);
  const [currentAuditId, setCurrentAuditId] = useState<string | null>(null);
  const reasoningRef = useRef<HTMLDivElement>(null);
  const [quotaExceeded, setQuotaExceeded] = useState(false);

  // Ownership state
  const [ownershipGraph, setOwnershipGraph] = useState<any>(null);
  const [ownershipFindings, setOwnershipFindings] = useState<any[]>([]);
  const [isDiscoveringOwnership, setIsDiscoveringOwnership] = useState(false);
  const [streamingNodes, setStreamingNodes] = useState<any[]>([]);
  const [streamingEdges, setStreamingEdges] = useState<any[]>([]);

  // Progress tracking state
  const [auditProgress, setAuditProgress] = useState(0);
  const [auditCurrentStep, setAuditCurrentStep] = useState(0);
  const [auditTotalSteps, setAuditTotalSteps] = useState(8);
  const [auditStepName, setAuditStepName] = useState("");
  const [auditStatus, setAuditStatus] = useState<"idle" | "running" | "paused" | "quota_exceeded" | "completed" | "error">("idle");



  const [ownershipGraphId, setOwnershipGraphId] = useState<string | null>(null);
  const [isOwnershipFullscreen, setIsOwnershipFullscreen] = useState(false);
  const [selectedOwnershipNode, setSelectedOwnershipNode] = useState<EntityNode | null>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  // Dialog state for interactive details
  const [selectedFinding, setSelectedFinding] = useState<any>(null);
  const [findingDialogOpen, setFindingDialogOpen] = useState(false);
  const [selectedInteraction, setSelectedInteraction] = useState<any>(null);
  const [interactionDialogOpen, setInteractionDialogOpen] = useState(false);
  const [selectedReasoningStep, setSelectedReasoningStep] = useState<any>(null);
  const [selectedReasoningIndex, setSelectedReasoningIndex] = useState(0);
  const [reasoningDialogOpen, setReasoningDialogOpen] = useState(false);

  useEffect(() => {
    fetchCompanyData();
  }, [id]);

  // Auto-scroll reasoning panel to bottom
  useEffect(() => {
    if (reasoningRef.current) {
      reasoningRef.current.scrollTop = reasoningRef.current.scrollHeight;
    }
  }, [liveReasoningSteps]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const fetchCompanyData = async () => {
    try {
      const [companyRes, coaRes, glRes, tbRes] = await Promise.all([
        fetch(`http://localhost:8000/api/companies/${id}`),
        fetch(`http://localhost:8000/api/companies/${id}/coa`),
        fetch(`http://localhost:8000/api/companies/${id}/gl`),
        fetch(`http://localhost:8000/api/companies/${id}/tb`)
      ]);

      if (companyRes.ok) setCompany(await companyRes.json());
      if (coaRes.ok) setCoa(await coaRes.json());
      if (glRes.ok) setGl(await glRes.json());
      if (tbRes.ok) setTb(await tbRes.json());
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const addReasoningStep = (step: string, type: "info" | "success" | "warning" | "ai" = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === "ai" ? "[AI]" : type === "success" ? "[OK]" : type === "warning" ? "[!]" : "[>]";
    setLiveReasoningSteps(prev => [...prev, `${timestamp} ${prefix} ${step}`]);
  };

  // State for streaming findings
  const [streamingFindings, setStreamingFindings] = useState<any[]>([]);
  const [streamingAjes, setStreamingAjes] = useState<any[]>([]);
  const [streamingRiskScore, setStreamingRiskScore] = useState<any>(null);

  // State for streaming reasoning chain and gemini interactions
  const [streamingReasoningChain, setStreamingReasoningChain] = useState<any[]>([]);
  const [streamingGeminiInteractions, setStreamingGeminiInteractions] = useState<any[]>([]);



  const runAudit = async () => {
    setIsAuditing(true);
    setAuditStatus("running");
    setAuditProgress(0);
    setAuditCurrentStep(0);
    setAuditStepName("Initializing...");
    setLiveReasoningSteps([]);
    setAuditTrail(null);
    setAuditResults(null);
    setStreamingFindings([]);
    setStreamingAjes([]);
    setStreamingRiskScore(null);
    setStreamingReasoningChain([]);
    setStreamingGeminiInteractions([]);

    addReasoningStep("Initializing audit engine...", "info");

    // Generate a temporary audit ID for early SSE connection
    // We'll get the real one from the POST response
    let eventSource: EventSource | null = null;
    let auditId: string | null = null;

    try {
      // Start the audit - this returns quickly with the audit_id
      const response = await fetch(`http://localhost:8000/api/audit/${id}/run`, {
        method: "POST"
      });

      if (response.ok) {
        const result = await response.json();
        auditId = result.audit_id;
        setCurrentAuditId(auditId);

        // Connect to SSE stream for live updates
        // The backend's subscribe() method will send all existing progress
        eventSource = new EventSource(`http://localhost:8000/api/audit/${id}/stream/${auditId}`);

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Update progress info if available
            if (data.progress_percent !== undefined) {
              setAuditProgress(data.progress_percent);
            }
            if (data.current_step !== undefined) {
              setAuditCurrentStep(data.current_step);
            }
            if (data.total_steps !== undefined) {
              setAuditTotalSteps(data.total_steps);
            }
            if (data.step_name) {
              setAuditStepName(data.step_name);
            }
            if (data.status) {
              setAuditStatus(data.status as any);
            }

            // Check for quota exceeded
            if (data.type === 'quota_exceeded' || data.status === 'quota_exceeded') {
              setAuditStatus("quota_exceeded");
              setQuotaExceeded(true);
              addReasoningStep("Quota exceeded - enter API key to continue", "warning");
            }

            if (data.type === 'end' || data.type === 'completed') {
              setAuditStatus("completed");
              eventSource?.close();
            } else if (data.type === 'heartbeat') {
              // Ignore heartbeats
            } else if (data.type === 'paused') {
              setAuditStatus("paused");
            } else if (data.type === 'data' && data.data) {
              // Handle streaming data updates
              const dataType = data.data.data_type;
              const payload = data.data.payload;

              console.log("[SSE] Received data:", dataType, payload?.finding_id || payload?.aje_id || "risk_score");

              if (dataType === 'finding' || dataType === 'finding_enhanced') {
                // Add or update finding in streaming list
                setStreamingFindings(prev => {
                  const existingIdx = prev.findIndex(f => f.finding_id === payload.finding_id);
                  if (existingIdx >= 0) {
                    // Update existing finding with enhanced data
                    const updated = [...prev];
                    updated[existingIdx] = payload;
                    return updated;
                  }
                  return [...prev, payload];
                });
              } else if (dataType === 'aje') {
                // Add AJE to streaming list
                setStreamingAjes(prev => [...prev, payload]);
              } else if (dataType === 'risk_score') {
                // Update risk score
                setStreamingRiskScore(payload);
              } else if (dataType === 'reasoning_step') {
                // Add reasoning step to streaming chain
                setStreamingReasoningChain(prev => [...prev, payload]);
              } else if (dataType === 'gemini_interaction') {
                // Add gemini interaction to streaming list
                setStreamingGeminiInteractions(prev => [...prev, payload]);
              }
            } else if (data.type === 'gemini_call' && data.data) {
              // Handle Gemini API call logging
              const geminiData = data.data;
              const timestamp = new Date().toLocaleTimeString();
              const promptPreview = geminiData.prompt?.substring(0, 100) || '';
              const responsePreview = geminiData.response?.substring(0, 150) || '';
              setLiveReasoningSteps(prev => [
                ...prev,
                `${timestamp} [GEMINI] ${geminiData.purpose}`,
                `  Prompt: ${promptPreview}${promptPreview.length >= 100 ? '...' : ''}`,
                `  Response: ${responsePreview}${responsePreview.length >= 150 ? '...' : ''}`
              ]);
            } else if (data.message) {
              const stepType = data.type === 'ai' ? 'ai' :
                data.type === 'success' || data.type === 'completed' ? 'success' :
                  data.type === 'error' || data.type === 'warning' ? 'warning' : 'info';
              addReasoningStep(data.message, stepType);
            }
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        };

        eventSource.onerror = (event) => {
          // SSE errors are normal when connection closes - don't treat as critical error
          // Only log if we're still expecting data (isAuditing is true)
          if (isAuditing) {
            console.warn("SSE connection closed");
          }
          eventSource?.close();
        };

        // Helper to safely fetch with timeout
        const safeFetch = async (url: string, name: string) => {
          try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            const res = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (res.ok) {
              return await res.json();
            } else {
              addReasoningStep(`Failed to fetch ${name}: HTTP ${res.status}`, "warning");
              return null;
            }
          } catch (err: any) {
            if (err.name === 'AbortError') {
              addReasoningStep(`${name} fetch timed out`, "warning");
            } else {
              addReasoningStep(`${name} fetch error: ${err.message}`, "warning");
            }
            return null;
          }
        };

        // Wait for the SSE stream to signal completion, then fetch full results
        const waitForCompletion = () => {
          return new Promise<void>((resolve) => {
            const originalOnMessage = eventSource!.onmessage;
            eventSource!.onmessage = (event) => {
              // Call original handler first
              if (originalOnMessage) {
                originalOnMessage.call(eventSource!, event);
              }

              try {
                const data = JSON.parse(event.data);
                if (data.type === 'end' || data.type === 'completed') {
                  resolve();
                }
              } catch (e) {
                // Ignore parse errors
              }
            };

            // Timeout after 5 minutes
            setTimeout(() => resolve(), 300000);
          });
        };

        addReasoningStep(`Audit ID: ${auditId}`, "info");
        addReasoningStep("Waiting for audit to complete...", "info");

        // Wait for the audit to complete
        await waitForCompletion();

        addReasoningStep("Audit completed! Fetching detailed results...", "success");

        // Fetch full results
        const [findingsData, ajesData, riskData, trailData] = await Promise.all([
          safeFetch(`http://localhost:8000/api/audit/${id}/findings?audit_id=${auditId}`, "findings"),
          safeFetch(`http://localhost:8000/api/audit/${id}/ajes?audit_id=${auditId}`, "AJEs"),
          safeFetch(`http://localhost:8000/api/audit/${id}/risk-score?audit_id=${auditId}`, "risk score"),
          safeFetch(`http://localhost:8000/api/audit/${id}/trail?audit_id=${auditId}`, "audit trail")
        ]);

        setAuditResults({
          findings: findingsData,
          ajes: ajesData,
          riskScore: riskData
        });

        setAuditTrail(trailData);

        // Check for quota exceeded in reasoning chain
        if (trailData?.audit_trail?.reasoning_chain) {
          const hasQuotaIssue = trailData.audit_trail.reasoning_chain.some(
            (step: any) => step.step?.toLowerCase().includes("quota exceeded")
          );
          if (hasQuotaIssue) {
            setQuotaExceeded(true);
          }
        }

        // Show summary
        if (findingsData) {
          addReasoningStep(`Found ${findingsData.total_count || findingsData.findings?.length || 0} findings`, "success");
        }
        if (riskData) {
          const riskLevel = riskData.risk_level || "unknown";
          addReasoningStep(`Risk Level: ${riskLevel.toUpperCase()}`, riskLevel === "critical" || riskLevel === "high" ? "warning" : "success");
        }
        if (ajesData) {
          addReasoningStep(`Generated ${ajesData.total_count || ajesData.ajes?.length || 0} adjusting journal entries`, "success");
        }
        if (trailData?.audit_trail) {
          addReasoningStep(`Audit trail: ${trailData.audit_trail.reasoning_chain?.length || 0} steps, ${trailData.audit_trail.gemini_interactions?.length || 0} AI calls`, "ai");
        }

        addReasoningStep("Audit complete. Review the tabs for details.", "success");
      } else {
        addReasoningStep("Audit request failed. Check backend logs.", "warning");
      }
    } catch (error) {
      addReasoningStep(`Error during audit: ${error}`, "warning");
      console.error("Audit error:", error);
    } finally {
      setIsAuditing(false);
    }
  };



  const discoverOwnership = async () => {
    setIsDiscoveringOwnership(true);
    setStreamingNodes([]);
    setStreamingEdges([]);
    setOwnershipGraph(null);
    setOwnershipFindings([]);
    addReasoningStep("Starting beneficial ownership discovery...", "info");

    const graphId = `vendor_graph_${id}`;
    setOwnershipGraphId(graphId);
    let eventSource: EventSource | null = null;

    try {
      // Start the discovery - returns immediately now
      const response = await fetch(`http://localhost:8000/api/ownership/analyze-vendors/${id}`, {
        method: "POST"
      });

      if (response.ok) {
        const result = await response.json();
        addReasoningStep(`Analyzing ${result.vendors_analyzed} vendors...`, "info");

        // Connect to SSE stream for live updates
        eventSource = new EventSource(`http://localhost:8000/api/ownership/stream/${graphId}`);

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Progress and status info handled here
            if (data.type === 'quota_exceeded' || data.status === 'quota_exceeded') {
              setQuotaExceeded(true);
            }

            if (data.type === 'end' || data.type === 'completed') {
              eventSource?.close();
            } else if (data.type === 'heartbeat') {
              // Ignore heartbeats
            } else if (data.type === 'paused') {
              // Ignore paused
            } else if (data.type === 'data' && data.data) {
              // Handle streaming graph data
              const dataType = data.data.data_type;
              const payload = data.data.payload;

              console.log("[Ownership SSE] Received:", dataType, payload?.name || payload?.id);

              if (dataType === 'node') {
                // Add node to streaming graph
                setStreamingNodes(prev => {
                  const existing = prev.find(n => n.id === payload.id);
                  if (existing) return prev;
                  return [...prev, payload];
                });
              } else if (dataType === 'edge') {
                // Add edge to streaming graph
                setStreamingEdges(prev => [...prev, payload]);
              } else if (dataType === 'circular_edge') {
                // Mark edges as circular (fraud pattern)
                setStreamingEdges(prev => {
                  return prev.map(e => {
                    // Check if this edge matches the circular pattern
                    if ((e.source === payload.source && e.target === payload.target) ||
                      (e.source === payload.target && e.target === payload.source)) {
                      return { ...e, is_circular: true };
                    }
                    return e;
                  });
                });
                addReasoningStep(`Circular pattern detected: ${payload.source} <-> ${payload.target}`, "warning");
              } else if (dataType === 'finding') {
                // Add finding
                setOwnershipFindings(prev => [...prev, payload]);
              }
            } else if (data.message) {
              const stepType = data.type === 'ai' ? 'ai' :
                data.type === 'success' || data.type === 'completed' ? 'success' :
                  data.type === 'error' || data.type === 'warning' ? 'warning' : 'info';
              addReasoningStep(data.message, stepType);

              // Check for boilerplate detection
              if (data.data?.type === 'boilerplate') {
                addReasoningStep(`[Boilerplate] Skipped full discovery for template company`, "info");
              }
            }
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        };

        eventSource.onerror = () => {
          // SSE errors are normal when connection closes - don't treat as critical
          if (isDiscoveringOwnership) {
            console.warn("Ownership SSE connection closed");
          }
          eventSource?.close();
        };

        // Wait for SSE to signal completion
        await new Promise<void>((resolve) => {
          const originalOnMessage = eventSource!.onmessage;
          eventSource!.onmessage = (event) => {
            if (originalOnMessage) {
              originalOnMessage.call(eventSource!, event);
            }
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'end' || data.type === 'completed') {
                resolve();
              }
            } catch (e) { }
          };
          // Timeout after 5 minutes
          setTimeout(() => resolve(), 300000);
        });

        // Fetch the final graph data
        addReasoningStep("Fetching complete ownership graph...", "info");
        const graphRes = await fetch(`http://localhost:8000/api/ownership/graph/${graphId}`);
        if (graphRes.ok) {
          const graphData = await graphRes.json();
          setOwnershipGraph(graphData);
          addReasoningStep(`Graph loaded: ${graphData.nodes?.length || 0} entities, ${graphData.edges?.length || 0} relationships`, "success");
        }

        // Fetch final findings
        const findingsRes = await fetch(`http://localhost:8000/api/ownership/graph/${graphId}/findings`);
        if (findingsRes.ok) {
          const findingsData = await findingsRes.json();
          setOwnershipFindings(findingsData.findings || []);
          if (findingsData.findings?.length > 0) {
            addReasoningStep(`Found ${findingsData.findings.length} ownership-related findings`, "warning");
          }
        }

        addReasoningStep("Ownership discovery complete.", "success");
      } else {
        addReasoningStep("Ownership discovery failed.", "warning");
      }
    } catch (error) {
      addReasoningStep(`Error: ${error}`, "warning");
      console.error("Ownership error:", error);
    } finally {
      eventSource?.close();
      setIsDiscoveringOwnership(false);
    }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || isChatLoading) return;

    const userMessage = chatInput;
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsChatLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          company_id: id,
          audit_id: currentAuditId
        })
      });

      if (response.ok) {
        const result = await response.json();
        setChatMessages(prev => [...prev, { role: "assistant", content: result.message }]);
      } else {
        setChatMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error processing your request." }]);
      }
    } catch (error) {
      setChatMessages(prev => [...prev, { role: "assistant", content: "Connection error. Please try again." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const exportPdf = () => {
    if (!currentAuditId) {
      alert("Please run an audit first.");
      return;
    }
    window.open(`http://localhost:8000/api/export/${id}/pdf?audit_id=${currentAuditId}`, "_blank");
  };

  // === MEMOIZED DATA MERGES (must be before any early returns for hooks rules) ===
  // Use streaming data while audit is running, fall back to final results when complete
  const riskScore = streamingRiskScore || auditResults?.riskScore;

  // Get base findings - prefer final results if available
  const baseFindingsList = auditResults?.findings?.findings || [];

  // Merge: ALWAYS prefer the version with ai_explanation
  const findings = useMemo(() => {
    if (baseFindingsList.length === 0 && streamingFindings.length === 0) {
      return [];
    }

    // Combine all findings by ID, preferring the one with ai_explanation
    const allFindingsMap = new Map<string, any>();

    // Add base findings first
    for (const f of baseFindingsList) {
      allFindingsMap.set(f.finding_id, f);
    }

    // Override with streaming findings ONLY if they have ai_explanation
    for (const f of streamingFindings) {
      const existing = allFindingsMap.get(f.finding_id);
      if (!existing || f.ai_explanation) {
        allFindingsMap.set(f.finding_id, f);
      }
    }

    return Array.from(allFindingsMap.values());
  }, [baseFindingsList, streamingFindings]);

  // Merge streaming AJEs with final results
  const baseAjesList = auditResults?.ajes?.ajes || [];
  const ajes = useMemo(() => {
    if (baseAjesList.length === 0 && streamingAjes.length === 0) {
      return [];
    }

    const allAjesMap = new Map<string, any>();

    // Add base AJEs first
    for (const a of baseAjesList) {
      allAjesMap.set(a.aje_id, a);
    }

    // Override with streaming AJEs
    for (const a of streamingAjes) {
      allAjesMap.set(a.aje_id, a);
    }

    return Array.from(allAjesMap.values());
  }, [baseAjesList, streamingAjes]);

  // Use streaming data during audit, fall back to trail data after completion
  const trail = auditTrail?.audit_trail;
  const reasoningChain = useMemo(() => {
    if (streamingReasoningChain.length > 0) {
      return streamingReasoningChain;
    }
    return trail?.reasoning_chain || [];
  }, [streamingReasoningChain, trail?.reasoning_chain]);

  const geminiInteractions = useMemo(() => {
    if (streamingGeminiInteractions.length > 0) {
      return streamingGeminiInteractions;
    }
    return trail?.gemini_interactions || [];
  }, [streamingGeminiInteractions, trail?.gemini_interactions]);

  // === EARLY RETURNS (after all hooks) ===
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] p-6">
        <Skeleton className="h-8 w-48 mb-4" />
        <Skeleton className="h-4 w-32 mb-8" />
        <div className="grid md:grid-cols-3 gap-6">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-[#1f1f1f] bg-[#0a0a0a]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground">
              <ChevronLeft className="h-4 w-4" />
              Back
            </Link>
            <span className="text-[#1f1f1f]">|</span>
            <Shield className="h-5 w-5 text-[#00d4ff]" />
            <span className="font-semibold">{company?.name || "Company"}</span>
            {currentAuditId && (
              <Badge variant="outline" className="ml-2 text-xs">
                Audit: {currentAuditId.substring(0, 8)}...
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={!currentAuditId}>
                  <Download className="mr-2 h-4 w-4" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={exportPdf}>
                  Export Report (PDF)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => window.open(`http://localhost:8000/api/export/${id}/csv/ajes?audit_id=${currentAuditId}`, "_blank")}>
                  Export AJEs (CSV)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => window.open(`http://localhost:8000/api/export/${id}/xlsx/ajes?audit_id=${currentAuditId}`, "_blank")}>
                  Export AJEs (Excel)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90"
              size="sm"
              onClick={runAudit}
              disabled={isAuditing}
            >
              <Play className="mr-2 h-4 w-4" />
              {isAuditing ? "Auditing..." : "Run Audit"}
            </Button>
          </div>
        </div>
      </header>

      {/* Progress Bar Section */}
      <div className="container mx-auto px-6 pt-4">
        <AuditProgress
          isRunning={isAuditing}
          progress={auditProgress}
          currentStep={auditCurrentStep}
          totalSteps={auditTotalSteps}
          stepName={auditStepName}
          status={auditStatus}
        />
      </div>

      <div className="container mx-auto px-6 py-6">
        {/* Company Info */}
        <div className="mb-6">
          <p className="text-muted-foreground">
            {company?.industry} | {company?.accounting_basis} basis | {company?.reporting_period}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-[#111111] border-[#1f1f1f]">
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">Risk Score</div>
              <div className={`text-3xl font-bold financial-number ${riskScore?.risk_level === "critical" ? "text-[#ff3366]" :
                riskScore?.risk_level === "high" ? "text-[#ff6b35]" :
                  riskScore?.risk_level === "medium" ? "text-[#fbbf24]" :
                    riskScore?.risk_level === "low" ? "text-[#22c55e]" :
                      "text-muted-foreground"
                }`}>
                {riskScore ? riskScore.overall_score.toFixed(1) : "--"}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {riskScore ? riskScore.risk_level.toUpperCase() : "Run audit"}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#111111] border-[#1f1f1f]">
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">Total Findings</div>
              <div className="text-3xl font-bold financial-number">
                {findings.length > 0 || auditResults ? findings.length : "--"}
                {isAuditing && findings.length > 0 && (
                  <span className="text-sm text-[#00d4ff] ml-2 animate-pulse">live</span>
                )}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {riskScore ? (
                  <span>
                    <span className="text-[#ff3366]">{riskScore.critical_count}C</span>
                    {" / "}
                    <span className="text-[#ff6b35]">{riskScore.high_count}H</span>
                    {" / "}
                    <span className="text-[#fbbf24]">{riskScore.medium_count}M</span>
                    {" / "}
                    <span className="text-[#22c55e]">{riskScore.low_count}L</span>
                  </span>
                ) : isAuditing && findings.length > 0 ? (
                  <span className="text-[#00d4ff]">Analyzing...</span>
                ) : ""}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#111111] border-[#1f1f1f]">
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">Adjusting Entries</div>
              <div className="text-3xl font-bold financial-number">
                {ajes.length > 0 || auditResults ? ajes.length : "--"}
                {isAuditing && ajes.length > 0 && (
                  <span className="text-sm text-[#00d4ff] ml-2 animate-pulse">live</span>
                )}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {auditResults ? (ajes.length > 0 ? "Generated" : "None needed") :
                  isAuditing && ajes.length > 0 ? <span className="text-[#00d4ff]">Generating...</span> : ""}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#111111] border-[#1f1f1f]">
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">GL Entries</div>
              <div className="text-3xl font-bold financial-number">
                {gl?.entries?.length ?? "--"}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {gl?.period_start} to {gl?.period_end}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Panel - Tabs */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="findings" className="space-y-4">
              <TabsList className="bg-[#111111] border border-[#1f1f1f]">
                <TabsTrigger value="findings" className="data-[state=active]:bg-[#1a1a1a]">
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Findings {findings.length > 0 && <Badge className="ml-2 bg-[#ff6b35]">{findings.length}</Badge>}
                </TabsTrigger>
                <TabsTrigger value="ownership" className="data-[state=active]:bg-[#1a1a1a]">
                  <Network className="mr-2 h-4 w-4" />
                  Ownership
                </TabsTrigger>
                <TabsTrigger value="trail" className="data-[state=active]:bg-[#1a1a1a]">
                  <Brain className="mr-2 h-4 w-4" />
                  Audit Trail
                </TabsTrigger>
                <TabsTrigger value="data" className="data-[state=active]:bg-[#1a1a1a]">
                  <FileText className="mr-2 h-4 w-4" />
                  Data
                </TabsTrigger>
              </TabsList>

              {/* Findings Tab */}
              <TabsContent value="findings">
                <Card className="bg-[#111111] border-[#1f1f1f]">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      Audit Findings
                      {isAuditing && findings.length > 0 && (
                        <Badge className="bg-[#00d4ff] text-black animate-pulse">
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Live
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>
                      {findings.length > 0
                        ? `${findings.length} findings identified${isAuditing ? " (updating...)" : ""}`
                        : "Run an audit to see findings"
                      }
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {findings.length > 0 ? (
                      <ScrollArea className="h-[500px]">
                        <Table>
                          <TableHeader>
                            <TableRow className="border-[#1f1f1f] hover:bg-transparent">
                              <TableHead className="text-muted-foreground">Severity</TableHead>
                              <TableHead className="text-muted-foreground">Category</TableHead>
                              <TableHead className="text-muted-foreground">Issue</TableHead>
                              <TableHead className="text-muted-foreground">Confidence</TableHead>
                              <TableHead className="text-muted-foreground w-24">Action</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {findings.map((finding: any, idx: number) => {
                              // Finding is ready when it has AI explanation or audit is complete
                              const isProcessing = isAuditing && (!finding.ai_explanation || finding.ai_explanation.includes("skipped"));
                              const isClickable = !isProcessing;

                              return (
                                <TableRow
                                  key={finding.finding_id || idx}
                                  className={`border-[#1f1f1f] transition-colors ${isClickable
                                    ? 'cursor-pointer hover:bg-[#1a1a1a]'
                                    : 'cursor-not-allowed opacity-70'
                                    }`}
                                  onClick={() => {
                                    if (!isClickable) return;
                                    setSelectedFinding(finding);
                                    setFindingDialogOpen(true);
                                  }}
                                >
                                  <TableCell>
                                    <Badge className={`
                                    ${finding.severity === "critical" ? "bg-[#ff3366] hover:bg-[#ff3366]" : ""}
                                    ${finding.severity === "high" ? "bg-[#ff6b35] hover:bg-[#ff6b35]" : ""}
                                    ${finding.severity === "medium" ? "bg-[#fbbf24] text-black hover:bg-[#fbbf24]" : ""}
                                    ${finding.severity === "low" ? "bg-[#22c55e] hover:bg-[#22c55e]" : ""}
                                  `}>
                                      {finding.severity?.toUpperCase()}
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="text-muted-foreground capitalize">{finding.category}</TableCell>
                                  <TableCell className="max-w-[300px]">
                                    <div className="font-medium truncate">{finding.issue}</div>
                                    <div className="text-xs text-muted-foreground mt-1 line-clamp-2 overflow-hidden">{finding.details?.substring(0, 80)}...</div>
                                    {finding.detection_method && (
                                      <div className="text-xs text-[#00d4ff] mt-1 flex items-center gap-1 overflow-hidden">
                                        <Code className="h-3 w-3 shrink-0" />
                                        <span className="truncate">{finding.detection_method.substring(0, 50)}...</span>
                                      </div>
                                    )}
                                  </TableCell>
                                  <TableCell className="financial-number">
                                    <div>{Math.round((finding.confidence || 0) * 100)}%</div>
                                    {finding.ai_explanation && !finding.ai_explanation.includes("skipped") ? (
                                      <div className="flex items-center gap-1 mt-1" title="AI explanation available">
                                        <Brain className="h-3 w-3 text-[#a855f7]" />
                                        <span className="text-[10px] text-[#a855f7]">AI Ready</span>
                                      </div>
                                    ) : isAuditing ? (
                                      <div className="flex items-center gap-1 mt-1" title="Generating AI explanation...">
                                        <Loader2 className="h-3 w-3 text-[#00d4ff] animate-spin" />
                                        <span className="text-[10px] text-[#00d4ff]">Loading</span>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-1 mt-1" title="AI explanation not available">
                                        <Lock className="h-3 w-3 text-muted-foreground" />
                                        <span className="text-[10px] text-muted-foreground">Pending</span>
                                      </div>
                                    )}
                                  </TableCell>
                                  <TableCell>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className={`${isClickable
                                        ? 'text-[#00d4ff] hover:text-[#00d4ff] hover:bg-[#00d4ff]/10'
                                        : 'text-muted-foreground cursor-not-allowed'
                                        }`}
                                      disabled={!isClickable}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (!isClickable) return;
                                        setSelectedFinding(finding);
                                        setFindingDialogOpen(true);
                                      }}
                                    >
                                      {isProcessing ? (
                                        <>
                                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                          Processing
                                        </>
                                      ) : (
                                        <>
                                          <Eye className="h-4 w-4 mr-1" />
                                          View
                                        </>
                                      )}
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </ScrollArea>
                    ) : (
                      <div className="text-center py-12 text-muted-foreground">
                        <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>{isAuditing ? "Findings will appear here as they are discovered..." : "No findings yet. Run an audit to analyze this company."}</p>
                        {isAuditing && (
                          <Loader2 className="h-6 w-6 mx-auto mt-4 animate-spin text-[#00d4ff]" />
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Ownership Tab */}
              <TabsContent value="ownership">
                <Card className="bg-[#111111] border-[#1f1f1f]">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>Beneficial Ownership Network</CardTitle>
                      <CardDescription>
                        Discover hidden ownership structures and related parties
                      </CardDescription>
                    </div>
                    <Button
                      onClick={discoverOwnership}
                      disabled={isDiscoveringOwnership}
                      className="bg-[#8b5cf6] hover:bg-[#8b5cf6]/90"
                    >
                      {isDiscoveringOwnership ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="mr-2 h-4 w-4" />
                      )}
                      {isDiscoveringOwnership ? "Discovering..." : "Discover Ownership"}
                    </Button>
                  </CardHeader>



                  <CardContent className="overflow-hidden">
                    {/* Use streaming data while discovering, final graph when complete */}
                    {/* Keep streaming data as fallback if API fetch fails */}
                    {(ownershipGraph || streamingNodes.length > 0) ? (
                      <div className="overflow-x-auto">
                        {/* Show live indicator while discovering */}
                        {isDiscoveringOwnership && (
                          <div className="flex items-center gap-2 mb-3 text-sm text-[#00d4ff]">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>Live: {streamingNodes.length} entities, {streamingEdges.length} relationships discovered</span>
                          </div>
                        )}
                        <div className="max-w-full">
                          <OwnershipGraph
                            nodes={(ownershipGraph?.nodes && ownershipGraph.nodes.length > 0) ? ownershipGraph.nodes : streamingNodes.map(n => ({
                              id: n.id,
                              name: n.name,
                              type: n.type || "company",
                              risk_level: n.red_flags?.length > 0 ? "high" : "low",
                              jurisdiction: n.jurisdiction,
                              red_flags: n.red_flags || [],
                              api_source: n.api_source,
                              registration_number: n.registration_number,
                              status: n.status,
                              is_boilerplate: n.is_boilerplate,
                              is_root: n.is_root,
                              registered_address: n.registered_address,
                              registration_date: n.registration_date,
                              beneficial_owners: n.beneficial_owners,
                              directors: n.directors,
                              lei: n.lei,
                              ticker: n.ticker,
                              gemini_classification: n.gemini_classification,
                              data_quality_score: n.data_quality_score,
                              is_mock: n.is_mock
                            }))}
                            edges={(ownershipGraph?.edges && ownershipGraph.edges.length > 0) ? ownershipGraph.edges : streamingEdges.map(e => ({
                              source: e.source,
                              target: e.target,
                              relationship: e.relationship,
                              ownership_percentage: e.percentage
                            }))}
                            width={600}
                            height={400}
                            onExpandClick={() => setIsOwnershipFullscreen(true)}
                            onNodeSelect={setSelectedOwnershipNode}
                            selectedNode={selectedOwnershipNode}
                            showInlineCard={true}
                          />
                        </div>
                        {ownershipFindings.length > 0 && (
                          <div className="mt-4">
                            <h4 className="font-medium mb-2 text-[#ff6b35]">
                              Ownership Findings ({ownershipFindings.length})
                              {isDiscoveringOwnership && <span className="text-[#00d4ff] text-sm ml-2 animate-pulse">live</span>}
                            </h4>
                            <div className="space-y-2 max-h-[200px] overflow-y-auto">
                              {ownershipFindings.map((finding: any, idx: number) => (
                                <div key={finding.finding_id || idx} className="p-3 bg-[#0a0a0a] rounded border border-[#1f1f1f]">
                                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                                    <Badge className={`shrink-0 ${finding.severity === "critical" ? "bg-[#ff3366]" : "bg-[#ff6b35]"}`}>
                                      {finding.severity?.toUpperCase()}
                                    </Badge>
                                    <span className="font-medium wrap-break-word">{finding.issue}</span>
                                  </div>
                                  <p className="text-sm text-muted-foreground wrap-break-word">{finding.details}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : isDiscoveringOwnership ? (
                      <div className="text-center py-12 text-muted-foreground">
                        <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-[#8b5cf6]" />
                        <p>Discovering ownership network...</p>
                        <p className="text-xs mt-2">Searching public registries for ownership data</p>
                      </div>
                    ) : (
                      <div className="text-center py-12 text-muted-foreground">
                        <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Click "Discover Ownership" to analyze vendor relationships</p>
                        <p className="text-xs mt-2">Uses Gemini AI to search public registries and build ownership graphs</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Audit Trail Tab */}
              <TabsContent value="trail">
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Reasoning Chain */}
                  <Card className="bg-[#111111] border-[#1f1f1f]">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Clock className="h-5 w-5 text-[#00d4ff]" />
                        Reasoning Chain
                      </CardTitle>
                      <CardDescription>
                        {reasoningChain.length > 0
                          ? `${reasoningChain.length} documented steps`
                          : isAuditing ? "Building reasoning chain..." : "Run an audit to see reasoning"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-[350px]">
                        {reasoningChain.length > 0 ? (
                          <div className="space-y-2">
                            {reasoningChain.map((step: any, idx: number) => (
                              <div
                                key={idx}
                                className="flex gap-3 p-2 rounded bg-[#0a0a0a] border border-[#1f1f1f] cursor-pointer hover:border-[#00d4ff] hover:bg-[#0f0f0f] transition-colors"
                                onClick={() => {
                                  setSelectedReasoningStep(step);
                                  setSelectedReasoningIndex(idx);
                                  setReasoningDialogOpen(true);
                                }}
                              >
                                <div className="w-6 h-6 rounded-full bg-[#00d4ff] text-black flex items-center justify-center text-xs font-bold shrink-0">
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0 overflow-hidden">
                                  <div className="text-xs text-muted-foreground font-mono truncate">{step.timestamp}</div>
                                  <div className="text-sm mt-1 wrap-break-word line-clamp-2">{step.step}</div>
                                </div>
                                <Eye className="h-4 w-4 text-[#00d4ff] opacity-50 shrink-0" />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 text-muted-foreground">
                            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm font-medium">No reasoning chain available</p>
                            {isAuditing ? (
                              <p className="text-xs mt-2 text-[#00d4ff]">Audit in progress - reasoning steps will appear here...</p>
                            ) : auditResults ? (
                              <p className="text-xs mt-2">Audit trail data may have been cleared. Run a new audit to see the reasoning chain.</p>
                            ) : (
                              <p className="text-xs mt-2">Run an audit to see the AI reasoning chain.</p>
                            )}
                          </div>
                        )}
                      </ScrollArea>
                    </CardContent>
                  </Card>

                  {/* Gemini Interactions */}
                  <Card className="bg-[#111111] border-[#1f1f1f]">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Brain className="h-5 w-5 text-[#a855f7]" />
                        Gemini AI Interactions
                      </CardTitle>
                      <CardDescription>
                        {geminiInteractions.length > 0
                          ? `${geminiInteractions.length} AI calls logged`
                          : "AI interactions will appear here"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-[350px]">
                        {geminiInteractions.length > 0 ? (
                          <div className="space-y-3">
                            {geminiInteractions.map((interaction: any, idx: number) => (
                              <div
                                key={idx}
                                className="p-3 rounded bg-[#0a0a0a] border border-[#1f1f1f] cursor-pointer hover:border-[#a855f7] transition-colors"
                                onClick={() => {
                                  setSelectedInteraction(interaction);
                                  setInteractionDialogOpen(true);
                                }}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <Badge variant="outline" className="text-[#a855f7] border-[#a855f7]">
                                    {interaction.purpose}
                                  </Badge>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground font-mono">
                                      {interaction.model}
                                    </span>
                                    <Eye className="h-4 w-4 text-[#a855f7]" />
                                  </div>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div className="bg-[#111111] p-2 rounded">
                                    <span className="text-muted-foreground">Prompt:</span>{" "}
                                    <span className="text-[#00d4ff]">{interaction.prompt_length} chars</span>
                                  </div>
                                  <div className="bg-[#111111] p-2 rounded">
                                    <span className="text-muted-foreground">Response:</span>{" "}
                                    <span className="text-[#22c55e]">{interaction.response_length} chars</span>
                                  </div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-2 italic">Click to view full prompt and response</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 text-muted-foreground">
                            <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm font-medium">No AI interactions recorded</p>
                            {isAuditing ? (
                              <p className="text-xs mt-2 text-[#00d4ff]">Audit in progress - Gemini calls will appear here...</p>
                            ) : auditResults ? (
                              <p className="text-xs mt-2">Audit trail data may have been cleared. Run a new audit to see Gemini interactions.</p>
                            ) : (
                              <p className="text-xs mt-2">Run an audit to see how Gemini AI assists the audit process.</p>
                            )}
                          </div>
                        )}
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </div>

                {/* Integrity Verification */}
                {trail && (
                  <Card className="bg-[#111111] border-[#1f1f1f] mt-4">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Hash className="h-5 w-5 text-[#22c55e]" />
                        Audit Integrity Verification
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                          <div className="text-sm text-muted-foreground mb-1">Record Integrity Hash</div>
                          <div className="font-mono text-xs text-[#22c55e] break-all">
                            {trail.record_integrity_hash || "Not computed"}
                          </div>
                        </div>
                        <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                          <div className="text-xs space-y-1">
                            <div>Audit ID: <span className="font-mono text-[#00d4ff]">{trail.audit_id}</span></div>
                            <div>Created: <span className="font-mono">{trail.created_at}</span></div>
                            <div>Input Type: <span className="font-mono">{trail.input_type}</span></div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Data Tab */}
              <TabsContent value="data">
                <Tabs defaultValue="coa" className="space-y-4">
                  <TabsList className="bg-[#0a0a0a]">
                    <TabsTrigger value="coa">Chart of Accounts</TabsTrigger>
                    <TabsTrigger value="gl">General Ledger</TabsTrigger>
                    <TabsTrigger value="tb">Trial Balance</TabsTrigger>
                    <TabsTrigger value="ajes">AJEs</TabsTrigger>
                  </TabsList>

                  <TabsContent value="coa">
                    <Card className="bg-[#111111] border-[#1f1f1f]">
                      <CardHeader>
                        <CardTitle>Chart of Accounts</CardTitle>
                        <CardDescription>{coa?.accounts?.length || 0} accounts</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-[400px]">
                          <Table>
                            <TableHeader>
                              <TableRow className="border-[#1f1f1f]">
                                <TableHead className="w-24">Code</TableHead>
                                <TableHead>Account Name</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Normal</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {coa?.accounts?.map((account: any, idx: number) => (
                                <TableRow key={idx} className="border-[#1f1f1f]">
                                  <TableCell className="font-mono">{account.code}</TableCell>
                                  <TableCell>{account.name}</TableCell>
                                  <TableCell className="capitalize text-muted-foreground">{account.type}</TableCell>
                                  <TableCell className="capitalize text-muted-foreground">{account.normal_balance}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="gl">
                    <Card className="bg-[#111111] border-[#1f1f1f]">
                      <CardHeader>
                        <CardTitle>General Ledger</CardTitle>
                        <CardDescription>{gl?.entries?.length || 0} entries | {gl?.period_start} to {gl?.period_end}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-[400px]">
                          <Table>
                            <TableHeader>
                              <TableRow className="border-[#1f1f1f]">
                                <TableHead>Date</TableHead>
                                <TableHead>Account</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead className="text-right">Debit</TableHead>
                                <TableHead className="text-right">Credit</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {gl?.entries?.slice(0, 100).map((entry: any, idx: number) => (
                                <TableRow key={idx} className="border-[#1f1f1f]">
                                  <TableCell className="font-mono text-sm">{entry.date}</TableCell>
                                  <TableCell className="font-mono text-sm">{entry.account_code}</TableCell>
                                  <TableCell className="text-sm">{entry.description?.slice(0, 30)}</TableCell>
                                  <TableCell className="text-right financial-number text-green-400">
                                    {entry.debit > 0 ? `$${entry.debit.toLocaleString()}` : ""}
                                  </TableCell>
                                  <TableCell className="text-right financial-number text-red-400">
                                    {entry.credit > 0 ? `$${entry.credit.toLocaleString()}` : ""}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="tb">
                    <Card className="bg-[#111111] border-[#1f1f1f]">
                      <CardHeader>
                        <CardTitle>Trial Balance</CardTitle>
                        <CardDescription>
                          {tb?.rows?.length || 0} accounts | {tb?.period_end}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-[400px]">
                          <Table>
                            <TableHeader>
                              <TableRow className="border-[#1f1f1f]">
                                <TableHead className="w-24">Account</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead className="text-right">Beginning Balance</TableHead>
                                <TableHead className="text-right">Debit</TableHead>
                                <TableHead className="text-right">Credit</TableHead>
                                <TableHead className="text-right">Balance ({tb?.period_end})</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {tb?.rows?.map((entry: any, idx: number) => (
                                <TableRow key={idx} className="border-[#1f1f1f]">
                                  <TableCell className="font-mono text-sm">{entry.account_code}</TableCell>
                                  <TableCell className="text-sm">{entry.account_name}</TableCell>
                                  <TableCell className="text-right financial-number font-mono text-muted-foreground">
                                    {(entry.beginning_balance || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                                  </TableCell>
                                  <TableCell className="text-right financial-number font-mono">
                                    {entry.debit > 0 ? entry.debit.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : "-"}
                                  </TableCell>
                                  <TableCell className="text-right financial-number font-mono">
                                    {entry.credit > 0 ? entry.credit.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : "-"}
                                  </TableCell>
                                  <TableCell className="text-right financial-number font-mono font-medium text-white">
                                    {(entry.ending_balance || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                                  </TableCell>
                                </TableRow>
                              ))}
                              {/* Total Row */}
                              {tb?.rows && (
                                <TableRow className="border-[#1f1f1f] bg-[#1a1a1a] font-bold">
                                  <TableCell colSpan={3} className="text-right">Total Activity</TableCell>
                                  <TableCell className="text-right financial-number text-[#00d4ff]">
                                    {tb.rows.reduce((sum: number, e: any) => sum + (e.debit || 0), 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                                  </TableCell>
                                  <TableCell className="text-right financial-number text-[#00d4ff]">
                                    {tb.rows.reduce((sum: number, e: any) => sum + (e.credit || 0), 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                                  </TableCell>
                                  <TableCell></TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="ajes">
                    <Card className="bg-[#111111] border-[#1f1f1f]">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <FileText className="h-5 w-5 text-[#00d4ff]" />
                          Adjusting Journal Entries
                          {isAuditing && ajes.length > 0 && (
                            <Badge className="bg-[#00d4ff] text-black animate-pulse">
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              Live
                            </Badge>
                          )}
                        </CardTitle>
                        <CardDescription>
                          {ajes.length > 0 || auditResults
                            ? `${ajes.length} correcting entries generated${isAuditing ? " (updating...)" : ""}`
                            : "Run an audit first"}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {ajes.length > 0 ? (
                          <ScrollArea className="h-[500px]">
                            <div className="space-y-4">
                              {ajes.map((aje: any, idx: number) => (
                                <AJEDetailCard
                                  key={aje.aje_id || idx}
                                  aje={aje}
                                  index={idx + 1}
                                  onFindingClick={(findingId) => {
                                    const finding = findings.find((f: any) => f.finding_id === findingId);
                                    if (finding) {
                                      setSelectedFinding(finding);
                                      setFindingDialogOpen(true);
                                    }
                                  }}
                                />
                              ))}
                            </div>
                          </ScrollArea>
                        ) : (
                          <div className="text-center py-12 text-muted-foreground">
                            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>{auditResults ? "No AJEs were generated." : isAuditing ? "AJEs will appear here as they are generated..." : "AJEs are generated after running an audit."}</p>
                            {auditResults && !isAuditing && (
                              <p className="text-xs mt-2">This may be due to no correctable issues or quota limitations.</p>
                            )}
                            {isAuditing && (
                              <Loader2 className="h-6 w-6 mx-auto mt-4 animate-spin text-[#00d4ff]" />
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </TabsContent>
            </Tabs>
          </div>

          {/* Right Panel - Chat */}
          <div className="lg:col-span-1">
            <Card className="bg-[#111111] border-[#1f1f1f] h-[700px] flex flex-col">
              <CardHeader className="shrink-0">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-[#00d4ff]" />
                  Auditor Assistant
                </CardTitle>
                <CardDescription>Ask questions about the audit</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col overflow-hidden">
                {/* Chat Messages */}
                <ScrollArea className="flex-1 pr-4" ref={chatRef}>
                  <div className="space-y-3">
                    {chatMessages.length === 0 && (
                      <div className="text-center text-muted-foreground text-sm py-8">
                        <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>Ask me anything about the audit findings!</p>
                        <p className="text-xs mt-1">e.g., "What is the highest risk finding?"</p>
                      </div>
                    )}
                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg ${msg.role === "user"
                          ? "bg-[#00d4ff]/10 border border-[#00d4ff]/20 ml-4"
                          : "bg-[#0a0a0a] border border-[#1f1f1f] mr-4"
                          }`}
                      >
                        <div className="text-xs text-muted-foreground mb-1">
                          {msg.role === "user" ? "You" : "Assistant"}
                        </div>
                        <div className="text-sm wrap-break-word whitespace-pre-wrap overflow-hidden">{msg.content}</div>
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="flex items-center gap-2 text-muted-foreground text-sm p-3">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Thinking...
                      </div>
                    )}
                  </div>
                </ScrollArea>

                {/* Chat Input */}
                <div className="flex gap-2 mt-4 shrink-0">
                  <Input
                    placeholder="Ask about the audit..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
                    className="bg-[#0a0a0a] border-[#1f1f1f]"
                  />
                  <Button
                    size="icon"
                    onClick={sendChatMessage}
                    disabled={isChatLoading || !chatInput.trim()}
                    className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

          </div>
        </div>

        {/* Live Console */}
        <Card className="bg-[#111111] border-[#1f1f1f] mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-[#00d4ff]" />
              Live Audit Console
              {isAuditing && (
                <Badge className="ml-2 bg-[#22c55e] animate-pulse">Running</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              ref={reasoningRef}
              className="font-mono text-sm bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f] h-32 overflow-y-auto overflow-x-hidden"
            >
              {liveReasoningSteps.length > 0 ? (
                liveReasoningSteps.map((step, idx) => {
                  const isAI = step.includes("[AI]");
                  const isSuccess = step.includes("[OK]");
                  const isWarning = step.includes("[!]");
                  return (
                    <p
                      key={idx}
                      className={`wrap-break-word whitespace-pre-wrap
                        ${isAI ? "text-[#a855f7]" : ""}
                        ${isSuccess ? "text-[#22c55e]" : ""}
                        ${isWarning ? "text-[#fbbf24]" : ""}
                        ${!isAI && !isSuccess && !isWarning ? "text-muted-foreground" : ""}
                      `}
                    >
                      {step}
                    </p>
                  );
                })
              ) : (
                <>
                  <p className="text-muted-foreground">{"> System ready."}</p>
                  <p className="text-muted-foreground">{"> Click 'Run Audit' to start analysis..."}</p>
                </>
              )}
              {isAuditing && (
                <p className="text-[#00d4ff] animate-pulse">{"> Processing..."}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Interactive Dialogs */}
      <FindingDetailDialog
        finding={selectedFinding}
        open={findingDialogOpen}
        onOpenChange={setFindingDialogOpen}
        isAuditing={isAuditing}
      />

      <GeminiInteractionDialog
        interaction={selectedInteraction}
        open={interactionDialogOpen}
        onOpenChange={setInteractionDialogOpen}
      />

      <ReasoningStepDialog
        step={selectedReasoningStep}
        stepIndex={selectedReasoningIndex}
        totalSteps={reasoningChain.length}
        open={reasoningDialogOpen}
        onOpenChange={setReasoningDialogOpen}
        allSteps={reasoningChain}
      />

      <QuotaExceededModal
        open={quotaExceeded}
        onClose={() => setQuotaExceeded(false)}
        onRetry={runAudit}
        operationType="audit"
      />

      {/* Fullscreen Ownership Graph Modal */}
      {isOwnershipFullscreen && (
        <div className="fixed inset-0 z-50 bg-[#0a0a0a]">
          <div className="w-full h-full">
            <OwnershipGraph
              nodes={ownershipGraph?.nodes || streamingNodes.map(n => ({
                id: n.id,
                name: n.name,
                type: n.type || "company",
                risk_level: n.red_flags?.length > 0 ? "high" : "low",
                jurisdiction: n.jurisdiction,
                red_flags: n.red_flags || [],
                api_source: n.api_source,
                registration_number: n.registration_number,
                status: n.status,
                is_boilerplate: n.is_boilerplate,
                is_root: n.is_root,
                registered_address: n.registered_address,
                registration_date: n.registration_date,
                beneficial_owners: n.beneficial_owners,
                directors: n.directors,
                lei: n.lei,
                ticker: n.ticker,
                gemini_classification: n.gemini_classification,
                data_quality_score: n.data_quality_score,
                is_mock: n.is_mock
              }))}
              edges={ownershipGraph?.edges || streamingEdges.map(e => ({
                source: e.source,
                target: e.target,
                relationship: e.relationship,
                ownership_percentage: e.percentage
              }))}
              width={typeof window !== 'undefined' ? window.innerWidth : 1200}
              height={typeof window !== 'undefined' ? window.innerHeight : 800}
              isFullscreen={true}
              onCloseFullscreen={() => setIsOwnershipFullscreen(false)}
            />
          </div>
        </div>
      )}
    </main>
  );
}
