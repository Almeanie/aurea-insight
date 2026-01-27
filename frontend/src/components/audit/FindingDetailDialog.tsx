"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  AlertTriangle, 
  FileText, 
  Code, 
  Brain,
  DollarSign,
  Calendar,
  Building,
  Hash,
  Loader2,
  Lock
} from "lucide-react";

interface TransactionDetail {
  entry_id: string;
  date: string;
  account_code: string;
  account_name: string;
  description: string;
  debit: number;
  credit: number;
  vendor?: string;
}

interface Finding {
  finding_id: string;
  category: string;
  severity: string;
  issue: string;
  details: string;
  recommendation: string;
  confidence: number;
  gaap_principle?: string;
  ai_explanation?: string;
  detection_method?: string;
  transaction_details?: TransactionDetail[];
  affected_transactions?: string[];
  audit_rule?: string;
  rule_code?: string;
}

interface FindingDetailDialogProps {
  finding: Finding | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isAuditing?: boolean;
}

export default function FindingDetailDialog({ 
  finding, 
  open, 
  onOpenChange,
  isAuditing = false
}: FindingDetailDialogProps) {
  if (!finding) return null;

  // Check if AI explanation is available
  const hasAiExplanation = finding.ai_explanation && !finding.ai_explanation.includes("skipped") && finding.ai_explanation.trim().length > 0;
  const isAiTabDisabled = !hasAiExplanation && !isAuditing;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] bg-[#111111] border-[#1f1f1f]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <Badge className={`
              ${finding.severity === "critical" ? "bg-[#ff3366] hover:bg-[#ff3366]" : ""}
              ${finding.severity === "high" ? "bg-[#ff6b35] hover:bg-[#ff6b35]" : ""}
              ${finding.severity === "medium" ? "bg-[#fbbf24] text-black hover:bg-[#fbbf24]" : ""}
              ${finding.severity === "low" ? "bg-[#22c55e] hover:bg-[#22c55e]" : ""}
            `}>
              {finding.severity?.toUpperCase()}
            </Badge>
            <DialogTitle className="text-xl">{finding.issue}</DialogTitle>
          </div>
          <DialogDescription className="flex items-center gap-4 mt-2">
            <span className="font-mono text-[#00d4ff]">{finding.finding_id}</span>
            <span className="text-muted-foreground">|</span>
            <span className="capitalize">{finding.category}</span>
            <span className="text-muted-foreground">|</span>
            <span>Confidence: {Math.round((finding.confidence || 0) * 100)}%</span>
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="details" className="mt-4">
          <TabsList className="bg-[#0a0a0a]">
            <TabsTrigger value="details" className="data-[state=active]:bg-[#1a1a1a]">
              <FileText className="mr-2 h-4 w-4" />
              Details
            </TabsTrigger>
            <TabsTrigger value="transactions" className="data-[state=active]:bg-[#1a1a1a]">
              <DollarSign className="mr-2 h-4 w-4" />
              Transactions
            </TabsTrigger>
            <TabsTrigger value="rule" className="data-[state=active]:bg-[#1a1a1a]">
              <Code className="mr-2 h-4 w-4" />
              Audit Rule
            </TabsTrigger>
            <TabsTrigger 
              value="ai" 
              className={`data-[state=active]:bg-[#1a1a1a] ${!hasAiExplanation ? 'opacity-60' : ''}`}
              disabled={isAiTabDisabled}
            >
              {isAuditing && !hasAiExplanation ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-[#00d4ff]" />
              ) : !hasAiExplanation ? (
                <Lock className="mr-2 h-4 w-4 text-muted-foreground" />
              ) : (
                <Brain className="mr-2 h-4 w-4 text-[#a855f7]" />
              )}
              {isAuditing && !hasAiExplanation ? "Loading..." : hasAiExplanation ? "AI Reasoning" : "AI Pending"}
            </TabsTrigger>
          </TabsList>

          {/* Details Tab */}
          <TabsContent value="details">
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-6">
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-[#ff6b35]" />
                    Finding Details
                  </h4>
                  <p className="text-muted-foreground">{finding.details}</p>
                </div>

                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-2">GAAP Principle</h4>
                  <p className="text-[#00d4ff]">{finding.gaap_principle || "N/A"}</p>
                </div>

                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-2">Recommendation</h4>
                  <p className="text-muted-foreground">{finding.recommendation}</p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Transactions Tab */}
          <TabsContent value="transactions">
            <ScrollArea className="h-[400px] pr-4">
              {finding.transaction_details && finding.transaction_details.length > 0 ? (
                <div className="space-y-4">
                  {finding.transaction_details.map((tx, idx) => (
                    <div key={idx} className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Hash className="h-4 w-4 text-[#00d4ff]" />
                          <span className="font-mono text-[#00d4ff]">{tx.entry_id}</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Calendar className="h-4 w-4" />
                          <span>{tx.date}</span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Account:</span>
                          <div className="font-mono">{tx.account_code} - {tx.account_name}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Vendor/Customer:</span>
                          <div className="flex items-center gap-1">
                            <Building className="h-4 w-4" />
                            {tx.vendor || "N/A"}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Debit:</span>
                          <div className="font-mono text-green-400">
                            {tx.debit > 0 ? `$${tx.debit.toLocaleString()}` : "-"}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Credit:</span>
                          <div className="font-mono text-red-400">
                            {tx.credit > 0 ? `$${tx.credit.toLocaleString()}` : "-"}
                          </div>
                        </div>
                      </div>
                      
                      <div className="mt-3 pt-3 border-t border-[#1f1f1f]">
                        <span className="text-muted-foreground text-sm">Description:</span>
                        <p className="mt-1">{tx.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Transaction details not available for this finding.</p>
                  {finding.affected_transactions && finding.affected_transactions.length > 0 && (
                    <p className="mt-2 font-mono text-sm">
                      Affected IDs: {finding.affected_transactions.join(", ")}
                    </p>
                  )}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* Audit Rule Tab */}
          <TabsContent value="rule">
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-4">
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Code className="h-4 w-4 text-[#00d4ff]" />
                    Audit Rule ID
                  </h4>
                  <p className="font-mono text-[#00d4ff]">{finding.audit_rule || "RULE_GENERIC"}</p>
                </div>

                {finding.rule_code ? (
                  <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                    <h4 className="font-medium mb-2">Deterministic Rule Code</h4>
                    <p className="text-xs text-muted-foreground mb-2">
                      This code runs deterministically to identify the finding. The AI does not perform the audit - it generates the rules.
                    </p>
                    <pre className="bg-[#111111] p-4 rounded overflow-x-auto text-xs font-mono text-green-400 whitespace-pre-wrap">
                      {finding.rule_code}
                    </pre>
                  </div>
                ) : (
                  <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                    <h4 className="font-medium mb-2">Rule Logic</h4>
                    <p className="text-muted-foreground">
                      This finding was generated by built-in deterministic rules based on GAAP principles.
                      The audit logic is verifiable and reproducible.
                    </p>
                    <div className="mt-4 p-3 bg-[#111111] rounded text-xs font-mono">
                      <p className="text-[#00d4ff]">{"// Rule Basis"}</p>
                      <p>Principle: {finding.gaap_principle}</p>
                      <p>Category: {finding.category}</p>
                      <p>Confidence: {Math.round((finding.confidence || 0) * 100)}%</p>
                    </div>
                  </div>
                )}

                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f] border-l-4 border-l-[#22c55e]">
                  <h4 className="font-medium mb-2 text-[#22c55e]">Regulatory Compliance Note</h4>
                  <p className="text-sm text-muted-foreground">
                    This audit finding was generated using deterministic rules. The same input data 
                    will always produce the same findings. AI is used only to explain findings 
                    and generate correcting entries - not to make audit decisions.
                  </p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* AI Reasoning Tab */}
          <TabsContent value="ai">
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-4">
                {/* Detection Method */}
                {finding.detection_method && (
                  <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <Code className="h-4 w-4 text-[#00d4ff]" />
                      Detection Method
                    </h4>
                    <p className="text-[#00d4ff] font-mono text-sm">{finding.detection_method}</p>
                  </div>
                )}

                {/* AI Explanation */}
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Brain className="h-4 w-4 text-[#a855f7]" />
                    AI Explanation
                  </h4>
                  {hasAiExplanation ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <p className="text-muted-foreground whitespace-pre-wrap">{finding.ai_explanation}</p>
                    </div>
                  ) : isAuditing ? (
                    <div className="flex items-center gap-3 text-[#00d4ff]">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <div>
                        <p className="font-medium">Generating AI explanation...</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Gemini is analyzing this finding and will provide context shortly.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-muted-foreground">
                      <p className="italic mb-2">AI explanation not available</p>
                      <p className="text-xs">This may be due to:</p>
                      <ul className="text-xs list-disc list-inside mt-1 space-y-1">
                        <li>API quota exceeded</li>
                        <li>Explanation was skipped for this finding type</li>
                        <li>Network error during generation</li>
                      </ul>
                    </div>
                  )}
                </div>

                {/* Confidence Score Visualization */}
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-3">Detection Confidence</h4>
                  <div className="flex items-center gap-4">
                    <div className="flex-1 bg-[#1f1f1f] rounded-full h-3 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-[#00d4ff] to-[#a855f7] transition-all"
                        style={{ width: `${Math.round((finding.confidence || 0) * 100)}%` }}
                      />
                    </div>
                    <span className="font-mono text-lg font-bold text-[#00d4ff]">
                      {Math.round((finding.confidence || 0) * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Confidence score based on detection algorithm and data quality
                  </p>
                </div>

                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f] border-l-4 border-l-[#a855f7]">
                  <h4 className="font-medium mb-2">AI Role Clarification</h4>
                  <p className="text-sm text-muted-foreground">
                    The AI (Gemini) provides explanations and context for findings but does NOT 
                    make audit decisions. All findings are generated by deterministic, verifiable 
                    rules that can be independently audited.
                  </p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
