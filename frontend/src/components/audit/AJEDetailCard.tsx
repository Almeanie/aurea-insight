"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  FileText,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle,
  Code,
  Link as LinkIcon
} from "lucide-react";

interface AJEEntry {
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
}

interface AJE {
  aje_id: string;
  date: string;
  entries: AJEEntry[];
  total_debits: number;
  total_credits: number;
  description: string;
  finding_reference?: string;
  rationale?: string;
  rule_applied?: string;
  is_balanced?: boolean;
  ai_explanation?: string;
  ai_basis?: string;
  ai_impact?: string;
}

interface AJEDetailCardProps {
  aje: AJE;
  onFindingClick?: (findingId: string) => void;
  index?: number;
}

export default function AJEDetailCard({ aje, onFindingClick, index }: AJEDetailCardProps) {
  const isBalanced = aje.is_balanced ?? (aje.total_debits === aje.total_credits);

  return (
    <Card className="bg-[#0a0a0a] border-[#1f1f1f]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[#00d4ff]" />
              <span className="font-semibold text-white">
                {index ? `AJE #${index}` : aje.aje_id}
              </span>
            </div>
            {index && (
              <span className="font-mono text-xs text-muted-foreground bg-[#1a1a1a] px-2 py-1 rounded">
                {aje.aje_id.substring(0, 8)}...
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isBalanced ? (
              <Badge className="bg-[#22c55e] hover:bg-[#22c55e]">
                <CheckCircle className="h-3 w-3 mr-1" />
                Balanced
              </Badge>
            ) : (
              <Badge className="bg-[#ff3366] hover:bg-[#ff3366]">
                Unbalanced
              </Badge>
            )}
            {aje.rule_applied && (
              <Badge variant="outline" className="text-[#a855f7] border-[#a855f7]">
                <Code className="h-3 w-3 mr-1" />
                {aje.rule_applied}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <div className="p-3 bg-[#111111] rounded border border-[#1f1f1f]">
          <p className="text-sm">{aje.description}</p>
          {aje.finding_reference && (
            <button
              onClick={() => onFindingClick?.(aje.finding_reference!)}
              className="mt-2 flex items-center gap-1 text-xs text-[#00d4ff] hover:underline"
            >
              <LinkIcon className="h-3 w-3" />
              Related Finding: {aje.finding_reference}
            </button>
          )}
        </div>

        {/* Journal Entries Table */}
        <div className="border border-[#1f1f1f] rounded overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-[#1f1f1f] bg-[#111111]">
                <TableHead className="text-muted-foreground">Account</TableHead>
                <TableHead className="text-muted-foreground text-right">Debit</TableHead>
                <TableHead className="text-muted-foreground text-right">Credit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {aje.entries?.map((entry, idx) => (
                <TableRow key={idx} className="border-[#1f1f1f]">
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {entry.debit > 0 ? (
                        <ArrowUpRight className="h-4 w-4 text-green-400" />
                      ) : (
                        <ArrowDownLeft className="h-4 w-4 text-red-400" />
                      )}
                      <div>
                        <div className="font-mono text-sm">{entry.account_code}</div>
                        <div className="text-xs text-muted-foreground">{entry.account_name}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {entry.debit > 0 ? (
                      <span className="text-green-400">${entry.debit.toLocaleString()}</span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {entry.credit > 0 ? (
                      <span className="text-red-400">${entry.credit.toLocaleString()}</span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {/* Totals Row */}
              <TableRow className="border-[#1f1f1f] bg-[#111111] font-bold">
                <TableCell>TOTALS</TableCell>
                <TableCell className="text-right font-mono text-green-400">
                  ${(aje.total_debits || 0).toLocaleString()}
                </TableCell>
                <TableCell className="text-right font-mono text-red-400">
                  ${(aje.total_credits || 0).toLocaleString()}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        {/* Rationale */}
        {aje.rationale && (
          <div className="p-3 bg-[#111111] rounded border border-[#1f1f1f] border-l-4 border-l-[#a855f7]">
            <h5 className="text-xs font-medium text-[#a855f7] mb-1">GAAP Rationale</h5>
            <p className="text-sm text-muted-foreground">{aje.rationale}</p>
          </div>
        )}

        {/* AI Explanation - if available */}
        {aje.ai_explanation && (
          <div className="p-3 bg-[#111111] rounded border border-[#1f1f1f] border-l-4 border-l-[#00d4ff]">
            <h5 className="text-xs font-medium text-[#00d4ff] mb-1">AI Explanation</h5>
            <p className="text-sm text-muted-foreground">{aje.ai_explanation}</p>
          </div>
        )}

        {/* AI Basis and Impact - if available */}
        {(aje.ai_basis || aje.ai_impact) && (
          <div className="grid grid-cols-2 gap-2">
            {aje.ai_basis && (
              <div className="p-2 bg-[#111111] rounded border border-[#1f1f1f]">
                <h5 className="text-xs font-medium text-muted-foreground mb-1">Accounting Basis</h5>
                <p className="text-xs text-[#22c55e]">{aje.ai_basis}</p>
              </div>
            )}
            {aje.ai_impact && (
              <div className="p-2 bg-[#111111] rounded border border-[#1f1f1f]">
                <h5 className="text-xs font-medium text-muted-foreground mb-1">Financial Impact</h5>
                <p className="text-xs text-[#ff6b35]">{aje.ai_impact}</p>
              </div>
            )}
          </div>
        )}

        {/* Date */}
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Effective Date: {aje.date || "Period End"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
