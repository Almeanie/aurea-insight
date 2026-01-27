"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
  currentStep?: number;
  totalSteps?: number;
  stepName?: string;
  variant?: "default" | "audit" | "ownership";
}

export function ProgressBar({
  value,
  max = 100,
  className,
  showLabel = true,
  currentStep,
  totalSteps,
  stepName,
  variant = "default",
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const variantColors = {
    default: "bg-[#00d4ff]",
    audit: "bg-[#8b5cf6]",
    ownership: "bg-[#22c55e]",
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Step info and percentage */}
      <div className="flex items-center justify-between mb-2 text-sm">
        <div className="flex items-center gap-2">
          {currentStep !== undefined && totalSteps !== undefined && (
            <span className="text-muted-foreground">
              Step {currentStep} of {totalSteps}
            </span>
          )}
          {stepName && (
            <>
              {currentStep !== undefined && <span className="text-muted-foreground">-</span>}
              <span className="text-foreground font-medium truncate max-w-[300px]">
                {stepName}
              </span>
            </>
          )}
        </div>
        {showLabel && (
          <span className="text-muted-foreground font-mono">
            {percentage.toFixed(0)}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-[#1f1f1f] rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-300 ease-out rounded-full",
            variantColors[variant]
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface AuditProgressProps {
  isRunning: boolean;
  progress: number;
  currentStep?: number;
  totalSteps?: number;
  stepName?: string;
  status?: "idle" | "running" | "paused" | "quota_exceeded" | "completed" | "error";
}

export function AuditProgress({
  isRunning,
  progress,
  currentStep,
  totalSteps,
  stepName,
  status = "idle",
}: AuditProgressProps) {
  if (status === "idle") {
    return null;
  }

  const statusColors = {
    running: "border-[#8b5cf6]",
    paused: "border-[#fbbf24]",
    quota_exceeded: "border-[#ff3366]",
    completed: "border-[#22c55e]",
    error: "border-[#ff3366]",
    idle: "border-[#1f1f1f]",
  };

  const statusLabels = {
    running: "Audit in Progress",
    paused: "Audit Paused",
    quota_exceeded: "Quota Exceeded",
    completed: "Audit Complete",
    error: "Audit Error",
    idle: "",
  };

  return (
    <div className={cn(
      "p-4 rounded-lg bg-[#111111] border mb-4",
      statusColors[status]
    )}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {status === "running" && (
            <div className="w-2 h-2 rounded-full bg-[#8b5cf6] animate-pulse" />
          )}
          {status === "paused" && (
            <div className="w-2 h-2 rounded-full bg-[#fbbf24]" />
          )}
          {status === "quota_exceeded" && (
            <div className="w-2 h-2 rounded-full bg-[#ff3366]" />
          )}
          {status === "completed" && (
            <div className="w-2 h-2 rounded-full bg-[#22c55e]" />
          )}
          <span className="font-medium">{statusLabels[status]}</span>
        </div>
      </div>

      <ProgressBar
        value={progress}
        currentStep={currentStep}
        totalSteps={totalSteps}
        stepName={stepName}
        variant="audit"
      />
    </div>
  );
}

interface OwnershipProgressProps {
  isRunning: boolean;
  progress: number;
  currentStep?: number;
  totalSteps?: number;
  stepName?: string;
  status?: "idle" | "running" | "paused" | "quota_exceeded" | "completed" | "error";
  onStop?: () => void;
  onResume?: () => void;
}

export function OwnershipProgress({
  isRunning,
  progress,
  currentStep,
  totalSteps,
  stepName,
  status = "idle",
  onStop,
  onResume,
}: OwnershipProgressProps) {
  if (status === "idle") {
    return null;
  }

  const statusColors = {
    running: "border-[#22c55e]",
    paused: "border-[#fbbf24]",
    quota_exceeded: "border-[#ff3366]",
    completed: "border-[#22c55e]",
    error: "border-[#ff3366]",
    idle: "border-[#1f1f1f]",
  };

  const statusLabels = {
    running: "Ownership Discovery in Progress",
    paused: "Discovery Paused",
    quota_exceeded: "Quota Exceeded",
    completed: "Discovery Complete",
    error: "Discovery Error",
    idle: "",
  };

  return (
    <div className={cn(
      "p-4 rounded-lg bg-[#111111] border mb-4",
      statusColors[status]
    )}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {status === "running" && (
            <div className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
          )}
          {status === "paused" && (
            <div className="w-2 h-2 rounded-full bg-[#fbbf24]" />
          )}
          {status === "quota_exceeded" && (
            <div className="w-2 h-2 rounded-full bg-[#ff3366]" />
          )}
          {status === "completed" && (
            <div className="w-2 h-2 rounded-full bg-[#22c55e]" />
          )}
          <span className="font-medium">{statusLabels[status]}</span>
        </div>

        <div className="flex items-center gap-2">
          {status === "running" && onStop && (
            <button
              onClick={onStop}
              className="px-3 py-1 text-sm rounded bg-[#ff3366]/20 text-[#ff3366] hover:bg-[#ff3366]/30 transition-colors"
            >
              Stop
            </button>
          )}
          {(status === "paused" || status === "quota_exceeded") && onResume && (
            <button
              onClick={onResume}
              className="px-3 py-1 text-sm rounded bg-[#00d4ff]/20 text-[#00d4ff] hover:bg-[#00d4ff]/30 transition-colors"
            >
              Resume
            </button>
          )}
        </div>
      </div>

      <ProgressBar
        value={progress}
        currentStep={currentStep}
        totalSteps={totalSteps}
        stepName={stepName}
        variant="ownership"
      />
    </div>
  );
}
