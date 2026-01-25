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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Brain,
  MessageSquare,
  ArrowRight,
  Clock,
  Hash
} from "lucide-react";

interface GeminiInteraction {
  timestamp: string;
  purpose: string;
  model: string;
  prompt_length: number;
  prompt_hash: string;
  prompt_preview: string;
  prompt_full?: string;
  response_length: number;
  response_hash?: string;
  response_preview?: string;
  response_full?: string;
  error?: string;
}

interface GeminiInteractionDialogProps {
  interaction: GeminiInteraction | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function GeminiInteractionDialog({ 
  interaction, 
  open, 
  onOpenChange 
}: GeminiInteractionDialogProps) {
  if (!interaction) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] bg-[#111111] border-[#1f1f1f]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <Brain className="h-6 w-6 text-[#a855f7]" />
            <DialogTitle className="text-xl">Gemini AI Interaction</DialogTitle>
          </div>
          <DialogDescription className="flex items-center gap-4 mt-2">
            <Badge variant="outline" className="text-[#a855f7] border-[#a855f7]">
              {interaction.purpose}
            </Badge>
            <span className="text-muted-foreground">|</span>
            <span className="font-mono text-sm">{interaction.model}</span>
            <span className="text-muted-foreground">|</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(interaction.timestamp).toLocaleString()}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="bg-[#0a0a0a] p-3 rounded border border-[#1f1f1f]">
            <div className="text-sm text-muted-foreground">Prompt Size</div>
            <div className="text-xl font-mono text-[#00d4ff]">{interaction.prompt_length.toLocaleString()} chars</div>
          </div>
          <div className="bg-[#0a0a0a] p-3 rounded border border-[#1f1f1f]">
            <div className="text-sm text-muted-foreground">Response Size</div>
            <div className="text-xl font-mono text-[#22c55e]">{interaction.response_length.toLocaleString()} chars</div>
          </div>
        </div>

        <Tabs defaultValue="prompt" className="mt-4">
          <TabsList className="bg-[#0a0a0a]">
            <TabsTrigger value="prompt" className="data-[state=active]:bg-[#1a1a1a]">
              <MessageSquare className="mr-2 h-4 w-4" />
              Prompt (Input)
            </TabsTrigger>
            <TabsTrigger value="response" className="data-[state=active]:bg-[#1a1a1a]">
              <ArrowRight className="mr-2 h-4 w-4" />
              Response (Output)
            </TabsTrigger>
            <TabsTrigger value="integrity" className="data-[state=active]:bg-[#1a1a1a]">
              <Hash className="mr-2 h-4 w-4" />
              Integrity
            </TabsTrigger>
          </TabsList>

          {/* Prompt Tab */}
          <TabsContent value="prompt">
            <ScrollArea className="h-[400px]">
              <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-[#00d4ff]">Prompt Sent to Gemini (FULL)</h4>
                  <Badge variant="outline">{interaction.prompt_length} chars</Badge>
                </div>
                <div className="bg-[#111111] rounded overflow-hidden border border-[#1f1f1f]">
                  <div className="bg-[#1a1a1a] px-3 py-2 border-b border-[#1f1f1f] flex justify-between items-center">
                    <span className="text-xs text-muted-foreground">Input to AI Model</span>
                    <Badge className="bg-[#00d4ff] text-black">INPUT</Badge>
                  </div>
                  <pre className="whitespace-pre-wrap text-sm font-mono text-muted-foreground p-4 overflow-x-auto max-h-[320px] overflow-y-auto">
                    {interaction.prompt_full || interaction.prompt_preview}
                  </pre>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Response Tab */}
          <TabsContent value="response">
            <ScrollArea className="h-[400px]">
              <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-[#22c55e]">Response from Gemini (FULL)</h4>
                  <Badge variant="outline">{interaction.response_length} chars</Badge>
                </div>
                {interaction.error ? (
                  <div className="bg-[#ff3366]/10 border border-[#ff3366] p-4 rounded">
                    <p className="text-[#ff3366] font-medium">Error Occurred</p>
                    <p className="text-sm text-muted-foreground mt-2">{interaction.error}</p>
                  </div>
                ) : (interaction.response_full || interaction.response_preview) ? (
                  <div className="bg-[#111111] rounded overflow-hidden border border-[#1f1f1f]">
                    <div className="bg-[#1a1a1a] px-3 py-2 border-b border-[#1f1f1f] flex justify-between items-center">
                      <span className="text-xs text-muted-foreground">Output from AI Model</span>
                      <Badge className="bg-[#22c55e] text-black">OUTPUT</Badge>
                    </div>
                    <pre className="whitespace-pre-wrap text-sm font-mono text-muted-foreground p-4 overflow-x-auto max-h-[320px] overflow-y-auto">
                      {interaction.response_full || interaction.response_preview}
                    </pre>
                  </div>
                ) : (
                  <p className="text-muted-foreground italic">No response available</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Integrity Tab */}
          <TabsContent value="integrity">
            <ScrollArea className="h-[400px]">
              <div className="space-y-4">
                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <h4 className="font-medium mb-3">Cryptographic Verification</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    These SHA-256 hashes allow regulators to verify that prompts and responses 
                    have not been tampered with since the audit was performed.
                  </p>
                  
                  <div className="space-y-4">
                    <div>
                      <span className="text-sm text-muted-foreground">Prompt Hash (SHA-256):</span>
                      <div className="font-mono text-xs text-[#00d4ff] bg-[#111111] p-3 rounded mt-1 break-all">
                        {interaction.prompt_hash}
                      </div>
                    </div>
                    
                    <div>
                      <span className="text-sm text-muted-foreground">Response Hash (SHA-256):</span>
                      <div className="font-mono text-xs text-[#22c55e] bg-[#111111] p-3 rounded mt-1 break-all">
                        {interaction.response_hash || "N/A (no response)"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f] border-l-4 border-l-[#22c55e]">
                  <h4 className="font-medium mb-2 text-[#22c55e]">Audit Trail Guarantee</h4>
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li>* Every AI interaction is logged with timestamps</li>
                    <li>* Cryptographic hashes ensure data integrity</li>
                    <li>* Prompts and responses are preserved for regulatory review</li>
                    <li>* The full audit trail can be exported for compliance</li>
                  </ul>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
