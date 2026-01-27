"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle, RefreshCw, Clock, Key, Loader2, CheckCircle, XCircle } from "lucide-react";

interface QuotaExceededModalProps {
  open: boolean;
  onClose: () => void;
  onRetry?: () => void;
  onResume?: () => void;
  operationType?: "audit" | "ownership";
}

export default function QuotaExceededModal({
  open,
  onClose,
  onRetry,
  onResume,
  operationType = "audit"
}: QuotaExceededModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmitKey = async () => {
    if (!apiKey.trim()) {
      setErrorMessage("Please enter an API key");
      setSubmitStatus("error");
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus("idle");
    setErrorMessage("");

    try {
      const response = await fetch("http://localhost:8000/api/settings/gemini-key", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ api_key: apiKey }),
      });

      const result = await response.json();

      if (result.success && result.validated) {
        setSubmitStatus("success");
        // Wait a moment then trigger resume
        setTimeout(() => {
          if (onResume) {
            onResume();
          }
          onClose();
        }, 1000);
      } else {
        setSubmitStatus("error");
        setErrorMessage(result.message || "Failed to validate API key");
      }
    } catch (error) {
      setSubmitStatus("error");
      setErrorMessage("Failed to connect to server");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setApiKey("");
    setSubmitStatus("idle");
    setErrorMessage("");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="max-w-lg bg-[#111111] border-[#ff3366] max-h-[90vh] overflow-y-auto">
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

          {/* API Key Input Section */}
          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Key className="h-4 w-4 text-[#00d4ff]" />
              Enter Your Own API Key
            </h4>
            <p className="text-sm text-muted-foreground mb-3">
              You can provide your own Gemini API key to continue. Get one free at{" "}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00d4ff] hover:underline"
              >
                Google AI Studio
              </a>
            </p>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder="Enter Gemini API key..."
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setSubmitStatus("idle");
                  setErrorMessage("");
                }}
                className="flex-1 bg-[#111111] border-[#1f1f1f]"
                disabled={isSubmitting}
              />
              <Button
                onClick={handleSubmitKey}
                disabled={isSubmitting || !apiKey.trim()}
                className="bg-[#00d4ff] hover:bg-[#00d4ff]/80 text-black"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : submitStatus === "success" ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  "Submit"
                )}
              </Button>
            </div>
            {submitStatus === "error" && errorMessage && (
              <div className="mt-2 flex items-center gap-2 text-sm text-[#ff3366]">
                <XCircle className="h-4 w-4" />
                {errorMessage}
              </div>
            )}
            {submitStatus === "success" && (
              <div className="mt-2 flex items-center gap-2 text-sm text-[#22c55e]">
                <CheckCircle className="h-4 w-4" />
                API key validated! Resuming {operationType}...
              </div>
            )}
          </div>

          <div className="bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#fbbf24]" />
              Other Options
            </h4>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li>- <strong>Wait a few minutes</strong> - Rate limits reset periodically</li>
              <li>- <strong>Continue without AI</strong> - The {operationType} can still run using deterministic rules</li>
            </ul>
          </div>

          <div className="bg-[#ff3366]/10 p-4 rounded border border-[#ff3366]/30">
            <p className="text-sm">
              <strong>Note:</strong> The core {operationType} functionality (GAAP checks, anomaly detection,
              fraud detection) works without AI. AI is used only for generating explanations
              and natural language responses.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleClose}
            className="border-[#1f1f1f]"
          >
            Continue Without AI
          </Button>
          {onRetry && (
            <Button
              onClick={() => {
                onRetry();
                handleClose();
              }}
              className="bg-[#8b5cf6] hover:bg-[#8b5cf6]/80"
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
