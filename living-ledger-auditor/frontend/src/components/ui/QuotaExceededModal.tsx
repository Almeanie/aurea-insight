"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, Clock } from "lucide-react";

interface QuotaExceededModalProps {
  open: boolean;
  onClose: () => void;
  onRetry?: () => void;
}

export default function QuotaExceededModal({ 
  open, 
  onClose,
  onRetry 
}: QuotaExceededModalProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-lg bg-[#111111] border-[#ff3366]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-[#ff3366]/20 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-[#ff3366]" />
            </div>
            <div>
              <DialogTitle className="text-xl text-[#ff3366]">
                AI Quota Exceeded
              </DialogTitle>
              <DialogDescription className="mt-1">
                The Gemini API rate limit has been reached
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
            <h4 className="font-medium mb-2">What happened?</h4>
            <p className="text-sm text-muted-foreground">
              The Gemini AI API has reached its request limit. This typically happens when:
            </p>
            <ul className="text-sm text-muted-foreground mt-2 space-y-1 list-disc list-inside">
              <li>Too many requests were made in a short period</li>
              <li>The daily quota has been exhausted</li>
              <li>The API key needs to be upgraded</li>
            </ul>
          </div>

          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#fbbf24]" />
              What can you do?
            </h4>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li>• <strong>Wait a few minutes</strong> - Rate limits reset periodically</li>
              <li>• <strong>Continue without AI</strong> - The audit can still run using deterministic rules</li>
              <li>• <strong>Use example data</strong> - Pre-generated data doesn't need AI calls</li>
            </ul>
          </div>

          <div className="bg-[#ff3366]/10 p-4 rounded border border-[#ff3366]/30">
            <p className="text-sm">
              <strong>Note:</strong> The core audit functionality (GAAP checks, anomaly detection, 
              fraud detection) works without AI. AI is used only for generating explanations 
              and natural language responses.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button 
            variant="outline" 
            onClick={onClose}
            className="border-[#1f1f1f]"
          >
            Continue Without AI
          </Button>
          {onRetry && (
            <Button 
              onClick={() => {
                onRetry();
                onClose();
              }}
              className="bg-[#00d4ff] hover:bg-[#00d4ff]/80 text-black"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
