"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Clock,
  CheckCircle,
  AlertTriangle,
  FileText,
  Database,
  ArrowRight,
  Code,
  BarChart3,
  ShieldCheck,
  Search
} from "lucide-react";

interface ReasoningStep {
  timestamp: string;
  step: string;
  details?: {
    description?: string;
    data_input?: Record<string, any>;
    checks_performed?: string[];
    rules_applied?: string[];
    algorithms_applied?: string[];
    patterns_checked?: string[];
    transactions_analyzed?: number;
    sample_transactions?: Array<{
      entry_id: string;
      date: string;
      account: string;
      debit: number;
      credit: number;
      description: string;
    }>;
    findings_count?: number;
    findings_summary?: Array<{
      id?: string;
      issue: string;
      severity?: string;
    }>;
    by_category?: Record<string, number>;
    by_severity?: Record<string, number>;
    methodology?: string;
    weights?: Record<string, number>;
    [key: string]: any;
  };
}

interface ReasoningStepDialogProps {
  step: ReasoningStep | null;
  stepIndex: number;
  totalSteps: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  allSteps?: ReasoningStep[];
}

export default function ReasoningStepDialog({
  step,
  stepIndex,
  totalSteps,
  open,
  onOpenChange,
  allSteps = []
}: ReasoningStepDialogProps) {
  if (!step) return null;

  const details = step.details || {};

  // Determine step type based on content
  const getStepType = (stepText: string) => {
    if (stepText.includes("structural")) return { type: "validation", color: "#3b82f6", icon: ShieldCheck };
    if (stepText.includes("GAAP")) return { type: "compliance", color: "#22c55e", icon: CheckCircle };
    if (stepText.includes("anomaly") || stepText.includes("statistical")) return { type: "detection", color: "#fbbf24", icon: BarChart3 };
    if (stepText.includes("fraud")) return { type: "fraud", color: "#ff3366", icon: AlertTriangle };
    if (stepText.includes("AI") || stepText.includes("Gemini")) return { type: "ai", color: "#a855f7", icon: Code };
    if (stepText.includes("AJE") || stepText.includes("journal")) return { type: "aje", color: "#00d4ff", icon: FileText };
    if (stepText.includes("risk")) return { type: "risk", color: "#ff6b35", icon: Search };
    return { type: "general", color: "#666666", icon: Clock };
  };

  const stepInfo = getStepType(step.step);
  const StepIcon = stepInfo.icon;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-full max-h-[90vh] bg-[#111111] border-[#1f1f1f] overflow-y-auto overflow-x-hidden">
        <DialogHeader className="sm:text-left">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center shrink-0 shadow-lg shadow-black/20"
              style={{ backgroundColor: stepInfo.color }}
            >
              <StepIcon className="w-6 h-6 text-white" />
            </div>
            <div className="min-w-0">
              <DialogTitle className="text-xl truncate">
                Step {stepIndex + 1}: {step.step}
              </DialogTitle>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span className="font-mono text-xs">{step.timestamp}</span>
                </div>
                <span className="text-muted-foreground hidden sm:inline">|</span>
                <Badge
                  variant="outline"
                  className="px-1.5 py-0 h-5"
                  style={{ borderColor: stepInfo.color, color: stepInfo.color }}
                >
                  {stepInfo.type.toUpperCase()}
                </Badge>
              </div>
            </div>
          </div>
        </DialogHeader>



        <div className="space-y-6 mt-4">

          {/* Description */}
          {details.description && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-2 text-[#00d4ff]">Description</h4>
              <p className="text-muted-foreground">{details.description}</p>
            </div>
          )}

          {/* Data Input Summary */}
          {details.data_input && Object.keys(details.data_input).length > 0 && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-3 flex items-center gap-2 text-[#00d4ff]">
                <Database className="h-4 w-4" />
                Data Input
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {Object.entries(details.data_input).map(([key, value]) => (
                  <div key={key} className="bg-[#111111] p-3 rounded border border-white/5">
                    <div className="text-[10px] text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</div>
                    <div className="text-xl font-bold text-white font-mono">{typeof value === 'number' ? value.toLocaleString() : String(value)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rules/Algorithms Applied */}
          {(details.rules_applied || details.algorithms_applied || details.patterns_checked || details.checks_performed) && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-3 flex items-center gap-2 text-[#00d4ff]">
                <Code className="h-4 w-4" />
                {details.rules_applied ? "Rules Applied" :
                  details.algorithms_applied ? "Algorithms Applied" :
                    details.patterns_checked ? "Patterns Checked" : "Checks Performed"}
              </h4>
              <div className="grid grid-cols-1 gap-2">
                {(details.rules_applied || details.algorithms_applied || details.patterns_checked || details.checks_performed || []).map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-[#111111] rounded">
                    <CheckCircle className="h-4 w-4 text-[#22c55e] shrink-0" />
                    <span className="text-sm">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sample Transactions Analyzed */}
          {details.sample_transactions && details.sample_transactions.length > 0 && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-3 flex items-center gap-2 text-[#00d4ff]">
                <FileText className="h-4 w-4" />
                Sample Transactions Analyzed
                <Badge variant="outline" className="ml-2">
                  {details.transactions_analyzed?.toLocaleString() || 0} total
                </Badge>
              </h4>
              <div className="border border-[#1f1f1f] rounded overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1f1f1f] bg-[#111111]">
                      <TableHead className="text-muted-foreground">Entry ID</TableHead>
                      <TableHead className="text-muted-foreground">Date</TableHead>
                      <TableHead className="text-muted-foreground">Account</TableHead>
                      <TableHead className="text-muted-foreground text-right">Debit</TableHead>
                      <TableHead className="text-muted-foreground text-right">Credit</TableHead>
                      <TableHead className="text-muted-foreground">Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {details.sample_transactions.map((tx, idx) => (
                      <TableRow key={idx} className="border-[#1f1f1f]">
                        <TableCell className="font-mono text-xs">{tx.entry_id}</TableCell>
                        <TableCell className="text-xs">{tx.date}</TableCell>
                        <TableCell className="font-mono text-xs">{tx.account}</TableCell>
                        <TableCell className="text-right font-mono text-green-400">
                          {tx.debit > 0 ? `$${tx.debit.toLocaleString()}` : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono text-red-400">
                          {tx.credit > 0 ? `$${tx.credit.toLocaleString()}` : '-'}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{tx.description}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Findings Summary */}
          {details.findings_summary && details.findings_summary.length > 0 && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-3 flex items-center gap-2 text-[#00d4ff]">
                <AlertTriangle className="h-4 w-4" />
                Findings Generated
                <Badge variant="outline" className="ml-2">
                  {details.findings_count || details.findings_summary.length} total
                </Badge>
              </h4>
              <div className="space-y-2">
                {details.findings_summary.map((finding, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-2 bg-[#111111] rounded">
                    <Badge className={`
                        ${finding.severity === "critical" ? "bg-[#ff3366]" : ""}
                        ${finding.severity === "high" ? "bg-[#ff6b35]" : ""}
                        ${finding.severity === "medium" ? "bg-[#fbbf24] text-black" : ""}
                        ${finding.severity === "low" ? "bg-[#22c55e]" : ""}
                      `}>
                      {finding.severity?.toUpperCase() || "INFO"}
                    </Badge>
                    <span className="text-sm flex-1">{finding.issue}</span>
                    {finding.id && (
                      <span className="font-mono text-xs text-muted-foreground">{finding.id}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Severity/Category Breakdown */}
          {(details.by_severity || details.by_category) && (
            <div className="grid grid-cols-2 gap-4">
              {details.by_severity && (
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-3 text-[#00d4ff]">By Severity</h4>
                  <div className="space-y-2">
                    {Object.entries(details.by_severity).map(([severity, count]) => (
                      <div key={severity} className="flex justify-between items-center">
                        <Badge className={`
                            ${severity === "critical" ? "bg-[#ff3366]" : ""}
                            ${severity === "high" ? "bg-[#ff6b35]" : ""}
                            ${severity === "medium" ? "bg-[#fbbf24] text-black" : ""}
                            ${severity === "low" ? "bg-[#22c55e]" : ""}
                          `}>
                          {severity.toUpperCase()}
                        </Badge>
                        <span className="font-mono text-lg">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {details.by_category && (
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-3 text-[#00d4ff]">By Category</h4>
                  <div className="space-y-2">
                    {Object.entries(details.by_category).map(([category, count]) => (
                      <div key={category} className="flex justify-between items-center">
                        <span className="capitalize text-muted-foreground">{category}</span>
                        <span className="font-mono text-lg">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Risk Score Methodology */}
          {details.methodology && (
            <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
              <h4 className="font-medium mb-2 text-[#00d4ff]">Scoring Methodology</h4>
              <p className="text-muted-foreground mb-3">{details.methodology}</p>
              {details.weights && (
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(details.weights).map(([severity, weight]) => (
                    <div key={severity} className="bg-[#111111] p-2 rounded text-center">
                      <div className="text-xs text-muted-foreground capitalize">{severity}</div>
                      <div className="text-lg font-mono" style={{
                        color:
                          severity === "critical" ? "#ff3366" :
                            severity === "high" ? "#ff6b35" :
                              severity === "medium" ? "#fbbf24" :
                                "#22c55e"
                      }}>
                        +{weight}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Workflow Position */}
          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
            <h4 className="font-medium mb-3 flex items-center gap-2 text-[#00d4ff]">
              <ArrowRight className="h-4 w-4" />
              Audit Workflow Position
            </h4>
            <div className="flex items-center gap-1 overflow-x-auto px-1 pb-2">
              {allSteps.map((s, idx) => (
                <div key={idx} className="flex items-center">
                  <div
                    className={`
                        shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono
                        ${idx === stepIndex
                        ? 'ring-2 ring-[#00d4ff] ring-offset-2 ring-offset-[#0a0a0a]'
                        : ''}
                        ${idx < stepIndex
                        ? 'bg-[#22c55e] text-white'
                        : idx === stepIndex
                          ? 'bg-[#00d4ff] text-black'
                          : 'bg-[#1f1f1f] text-muted-foreground'}
                      `}
                  >
                    {idx + 1}
                  </div>
                  {idx < allSteps.length - 1 && (
                    <div className={`w-4 h-0.5 ${idx < stepIndex ? 'bg-[#22c55e]' : 'bg-[#1f1f1f]'}`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Regulatory Note */}
          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f] border-l-4 border-l-[#22c55e]">
            <h4 className="font-medium mb-2 flex items-center gap-2 text-[#22c55e]">
              <ShieldCheck className="h-4 w-4" />
              Regulatory Compliance
            </h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• This step is permanently recorded in the immutable audit trail</li>
              <li>• Timestamp is cryptographically verified</li>
              <li>• All deterministic rules are fully reproducible</li>
              <li>• Input data hash ensures data integrity</li>
            </ul>
          </div>
        </div>

      </DialogContent>
    </Dialog>
  );
}
