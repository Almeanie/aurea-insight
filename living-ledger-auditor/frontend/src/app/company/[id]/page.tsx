"use client";

import { use, useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import OwnershipGraph from "@/components/ownership/OwnershipGraph";
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
  Code
} from "lucide-react";
import Link from "next/link";
import QuotaExceededModal from "@/components/ui/QuotaExceededModal";

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

  // Chat state
  const [chatMessages, setChatMessages] = useState<{role: string; content: string}[]>([]);
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

  const runAudit = async () => {
    setIsAuditing(true);
    setLiveReasoningSteps([]);
    setAuditTrail(null);
    setAuditResults(null);
    
    addReasoningStep("Initializing audit engine...", "info");

    try {
      // Start the audit
      const response = await fetch(`http://localhost:8000/api/audit/${id}/run`, {
        method: "POST"
      });
      
      if (response.ok) {
        const result = await response.json();
        setCurrentAuditId(result.audit_id);
        
        // Connect to SSE stream for live updates
        const eventSource = new EventSource(`http://localhost:8000/api/audit/${id}/stream/${result.audit_id}`);
        
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'end') {
              eventSource.close();
            } else if (data.type === 'heartbeat') {
              // Ignore heartbeats
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
        
        eventSource.onerror = () => {
          eventSource.close();
        };
        
        addReasoningStep(`Audit completed successfully!`, "success");
        addReasoningStep(`Found ${result.findings_count} findings`, "success");
        addReasoningStep(`Risk Level: ${result.risk_level.toUpperCase()}`, result.risk_level === "critical" || result.risk_level === "high" ? "warning" : "success");
        addReasoningStep(`Generated ${result.ajes_count} adjusting journal entries`, "success");
        addReasoningStep(`Audit ID: ${result.audit_id}`, "info");
        
        // Fetch full results with individual error handling
        addReasoningStep("Fetching detailed audit results...", "info");
        
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

        const [findingsData, ajesData, riskData, trailData] = await Promise.all([
          safeFetch(`http://localhost:8000/api/audit/${id}/findings?audit_id=${result.audit_id}`, "findings"),
          safeFetch(`http://localhost:8000/api/audit/${id}/ajes?audit_id=${result.audit_id}`, "AJEs"),
          safeFetch(`http://localhost:8000/api/audit/${id}/risk-score?audit_id=${result.audit_id}`, "risk score"),
          safeFetch(`http://localhost:8000/api/audit/${id}/trail?audit_id=${result.audit_id}`, "audit trail")
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

        // Show warnings if any fetches failed
        const fetchedCount = [findingsData, ajesData, riskData, trailData].filter(Boolean).length;
        if (fetchedCount < 4) {
          addReasoningStep(`Warning: Only ${fetchedCount}/4 result endpoints responded`, "warning");
        }

        if (trailData?.audit_trail) {
          addReasoningStep(`Audit trail recorded: ${trailData.audit_trail.reasoning_chain?.length || 0} steps`, "success");
          addReasoningStep(`Gemini interactions logged: ${trailData.audit_trail.gemini_interactions?.length || 0}`, "ai");
          if (trailData.audit_trail.record_integrity_hash) {
            addReasoningStep(`Integrity hash: ${trailData.audit_trail.record_integrity_hash.substring(0, 16)}...`, "success");
          }
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
    addReasoningStep("Starting beneficial ownership discovery...", "info");

    // First, set up SSE to receive live updates
    const graphId = `vendor_graph_${id}`;
    const eventSource = new EventSource(`http://localhost:8000/api/ownership/stream/${graphId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'end') {
          eventSource.close();
        } else if (data.type === 'heartbeat') {
          // Ignore heartbeats
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
      eventSource.close();
    };

    try {
      const response = await fetch(`http://localhost:8000/api/ownership/analyze-vendors/${id}`, {
        method: "POST"
      });

      if (response.ok) {
        const result = await response.json();
        addReasoningStep(`Analyzed ${result.vendors_analyzed} vendors`, "success");
        addReasoningStep(`Discovered ${result.entities_discovered} entities`, "success");
        addReasoningStep(`Found ${result.findings_count} ownership-related findings`, result.findings_count > 0 ? "warning" : "success");

        // Fetch the graph data
        const graphRes = await fetch(`http://localhost:8000/api/ownership/graph/${result.graph_id}`);
        if (graphRes.ok) {
          const graphData = await graphRes.json();
          setOwnershipGraph(graphData);
        }

        // Fetch findings
        const findingsRes = await fetch(`http://localhost:8000/api/ownership/graph/${result.graph_id}/findings`);
        if (findingsRes.ok) {
          const findingsData = await findingsRes.json();
          setOwnershipFindings(findingsData.findings || []);
        }

        addReasoningStep("Ownership graph loaded.", "success");
      } else {
        addReasoningStep("Ownership discovery failed.", "warning");
      }
    } catch (error) {
      addReasoningStep(`Error: ${error}`, "warning");
      console.error("Ownership error:", error);
    } finally {
      eventSource.close();
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

  const riskScore = auditResults?.riskScore;
  const findings = auditResults?.findings?.findings || [];
  const ajes = auditResults?.ajes?.ajes || [];
  const trail = auditTrail?.audit_trail;
  const reasoningChain = trail?.reasoning_chain || [];
  const geminiInteractions = trail?.gemini_interactions || [];

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
            <Button variant="outline" size="sm" onClick={exportPdf} disabled={!currentAuditId}>
              <Download className="mr-2 h-4 w-4" />
              Export PDF
            </Button>
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
              <div className={`text-3xl font-bold financial-number ${
                riskScore?.risk_level === "critical" ? "text-[#ff3366]" :
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
                {auditResults ? findings.length : "--"}
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
                ) : ""}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#111111] border-[#1f1f1f]">
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">Adjusting Entries</div>
              <div className="text-3xl font-bold financial-number">
                {auditResults ? ajes.length : "--"}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {auditResults ? (ajes.length > 0 ? "Generated" : "None needed") : ""}
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
                    <CardTitle>Audit Findings</CardTitle>
                    <CardDescription>
                      {findings.length > 0 
                        ? `${findings.length} findings identified`
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
                            {findings.map((finding: any, idx: number) => (
                              <TableRow 
                                key={idx} 
                                className="border-[#1f1f1f] cursor-pointer hover:bg-[#1a1a1a] transition-colors"
                                onClick={() => {
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
                                      <Code className="h-3 w-3 flex-shrink-0" />
                                      <span className="truncate">{finding.detection_method.substring(0, 50)}...</span>
                                    </div>
                                  )}
                                </TableCell>
                                <TableCell className="financial-number">
                                  <div>{Math.round((finding.confidence || 0) * 100)}%</div>
                                  {finding.ai_explanation && (
                                    <div className="flex items-center gap-1 mt-1">
                                      <Brain className="h-3 w-3 text-[#a855f7]" />
                                      <span className="text-[10px] text-[#a855f7]">AI</span>
                                    </div>
                                  )}
                                </TableCell>
                                <TableCell>
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    className="text-[#00d4ff] hover:text-[#00d4ff] hover:bg-[#00d4ff]/10"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedFinding(finding);
                                      setFindingDialogOpen(true);
                                    }}
                                  >
                                    <Eye className="h-4 w-4 mr-1" />
                                    View
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </ScrollArea>
                    ) : (
                      <div className="text-center py-12 text-muted-foreground">
                        <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No findings yet. Run an audit to analyze this company.</p>
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
                  <CardContent>
                    {ownershipGraph ? (
                      <div>
                        <OwnershipGraph 
                          nodes={ownershipGraph.nodes || []}
                          edges={ownershipGraph.edges || []}
                          width={700}
                          height={400}
                        />
                        {ownershipFindings.length > 0 && (
                          <div className="mt-4">
                            <h4 className="font-medium mb-2 text-[#ff6b35]">Ownership Findings ({ownershipFindings.length})</h4>
                            <div className="space-y-2 max-h-[200px] overflow-y-auto">
                              {ownershipFindings.map((finding: any, idx: number) => (
                                <div key={idx} className="p-3 bg-[#0a0a0a] rounded border border-[#1f1f1f]">
                                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                                    <Badge className={`flex-shrink-0 ${finding.severity === "critical" ? "bg-[#ff3366]" : "bg-[#ff6b35]"}`}>
                                      {finding.severity?.toUpperCase()}
                                    </Badge>
                                    <span className="font-medium break-words">{finding.issue}</span>
                                  </div>
                                  <p className="text-sm text-muted-foreground break-words">{finding.details}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
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
                          : "Run an audit first"}
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
                                <div className="w-6 h-6 rounded-full bg-[#00d4ff] text-black flex items-center justify-center text-xs font-bold flex-shrink-0">
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0 overflow-hidden">
                                  <div className="text-xs text-muted-foreground font-mono truncate">{step.timestamp}</div>
                                  <div className="text-sm mt-1 break-words line-clamp-2">{step.step}</div>
                                </div>
                                <Eye className="h-4 w-4 text-[#00d4ff] opacity-50 flex-shrink-0" />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-8 text-muted-foreground">
                            <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No reasoning chain available</p>
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
                            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No AI interactions recorded</p>
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

                  <TabsContent value="ajes">
                    <Card className="bg-[#111111] border-[#1f1f1f]">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <FileText className="h-5 w-5 text-[#00d4ff]" />
                          Adjusting Journal Entries
                        </CardTitle>
                        <CardDescription>
                          {auditResults 
                            ? `${ajes.length} correcting entries generated` 
                            : "Run an audit first"}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {ajes.length > 0 ? (
                          <ScrollArea className="h-[500px]">
                            <div className="space-y-4">
                              {ajes.map((aje: any, idx: number) => (
                                <AJEDetailCard 
                                  key={idx} 
                                  aje={aje}
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
                            <p>{auditResults ? "No AJEs were generated." : "AJEs are generated after running an audit."}</p>
                            {auditResults && (
                              <p className="text-xs mt-2">This may be due to no correctable issues or quota limitations.</p>
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
              <CardHeader className="flex-shrink-0">
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
                        className={`p-3 rounded-lg ${
                          msg.role === "user"
                            ? "bg-[#00d4ff]/10 border border-[#00d4ff]/20 ml-4"
                            : "bg-[#0a0a0a] border border-[#1f1f1f] mr-4"
                        }`}
                      >
                        <div className="text-xs text-muted-foreground mb-1">
                          {msg.role === "user" ? "You" : "Assistant"}
                        </div>
                        <div className="text-sm break-words whitespace-pre-wrap overflow-hidden">{msg.content}</div>
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
                <div className="flex gap-2 mt-4 flex-shrink-0">
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
                      className={`break-words whitespace-pre-wrap
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
      />
    </main>
  );
}
