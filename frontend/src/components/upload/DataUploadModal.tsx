"use client";

import { useState, useRef } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FileUp, FileText, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataUploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    onUpload: (glFile: File, tbFile: File | null) => Promise<void>;
    isUploading: boolean;
}

export default function DataUploadModal({
    isOpen,
    onClose,
    onUpload,
    isUploading
}: DataUploadModalProps) {
    const [glFile, setGlFile] = useState<File | null>(null);
    const [tbFile, setTbFile] = useState<File | null>(null);
    const [glDragActive, setGlDragActive] = useState(false);
    const [tbDragActive, setTbDragActive] = useState(false);

    const glInputRef = useRef<HTMLInputElement>(null);
    const tbInputRef = useRef<HTMLInputElement>(null);

    const handleGlFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            setGlFile(e.target.files[0]);
        }
    };

    const handleTbFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            setTbFile(e.target.files[0]);
        }
    };

    const handleGlDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setGlDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            setGlFile(e.dataTransfer.files[0]);
        }
    };

    const handleTbDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setTbDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            setTbFile(e.dataTransfer.files[0]);
        }
    };

    const handleUploadSubmit = async () => {
        if (glFile) {
            await onUpload(glFile, tbFile);
            // We don't close here, we let the parent handle it after success/failure
        }
    };

    const resetFiles = () => {
        setGlFile(null);
        setTbFile(null);
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="sm:max-w-[600px] bg-[#111111] border-[#1f1f1f] text-white">
                <DialogHeader>
                    <DialogTitle className="text-xl font-bold">Upload Financial Data</DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Upload your company's data for AI-powered audit analysis.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 py-6">
                    {/* General Ledger Upload */}
                    <div className="space-y-3">
                        <label className="text-sm font-medium flex items-center gap-2">
                            <FileUp className="h-4 w-4 text-[#00d4ff]" />
                            General Ledger (Required)
                        </label>
                        <div
                            className={cn(
                                "relative group cursor-pointer border-2 border-dashed rounded-lg p-6 transition-all duration-200 flex flex-col items-center justify-center text-center gap-2",
                                glFile ? "border-[#00d4ff]/50 bg-[#00d4ff]/5" : "border-[#1f1f1f] hover:border-[#00d4ff]/30 hover:bg-[#111111]",
                                glDragActive && "border-[#00d4ff] bg-[#00d4ff]/10 scale-[0.98]"
                            )}
                            onDragOver={(e) => { e.preventDefault(); setGlDragActive(true); }}
                            onDragLeave={() => setGlDragActive(false)}
                            onDrop={handleGlDrop}
                            onClick={() => glInputRef.current?.click()}
                        >
                            {glFile ? (
                                <>
                                    <FileText className="h-8 w-8 text-[#00d4ff]" />
                                    <div className="text-sm font-medium truncate max-w-full px-2">
                                        {glFile.name}
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setGlFile(null); }}
                                        className="absolute top-2 right-2 p-1 rounded-full bg-[#1f1f1f] hover:bg-[#2a2a2a] text-muted-foreground hover:text-white"
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                </>
                            ) : (
                                <>
                                    <FileUp className="h-8 w-8 text-muted-foreground group-hover:text-[#00d4ff] transition-colors" />
                                    <div className="text-xs text-muted-foreground">
                                        Drag & drop csv/xlsx or <span className="text-[#00d4ff]">browse</span>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground/60 leading-tight">
                                        Transaction detail with dates, account codes, and amounts.
                                    </p>
                                </>
                            )}
                            <input
                                ref={glInputRef}
                                type="file"
                                className="hidden"
                                accept=".csv,.xlsx,.xls,.json,.txt"
                                onChange={handleGlFileSelect}
                            />
                        </div>
                    </div>

                    {/* Trial Balance Upload */}
                    <div className="space-y-3">
                        <label className="text-sm font-medium flex items-center gap-2">
                            <FileUp className="h-4 w-4 text-[#a855f7]" />
                            Trial Balance (Optional)
                        </label>
                        <div
                            className={cn(
                                "relative group cursor-pointer border-2 border-dashed rounded-lg p-6 transition-all duration-200 flex flex-col items-center justify-center text-center gap-2",
                                tbFile ? "border-[#a855f7]/50 bg-[#a855f7]/5" : "border-[#1f1f1f] hover:border-[#a855f7]/30 hover:bg-[#111111]",
                                tbDragActive && "border-[#a855f7] bg-[#a855f7]/10 scale-[0.98]"
                            )}
                            onDragOver={(e) => { e.preventDefault(); setTbDragActive(true); }}
                            onDragLeave={() => setTbDragActive(false)}
                            onDrop={handleTbDrop}
                            onClick={() => tbInputRef.current?.click()}
                        >
                            {tbFile ? (
                                <>
                                    <FileText className="h-8 w-8 text-[#a855f7]" />
                                    <div className="text-sm font-medium truncate max-w-full px-2">
                                        {tbFile.name}
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setTbFile(null); }}
                                        className="absolute top-2 right-2 p-1 rounded-full bg-[#1f1f1f] hover:bg-[#2a2a2a] text-muted-foreground hover:text-white"
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                </>
                            ) : (
                                <>
                                    <FileUp className="h-8 w-8 text-muted-foreground group-hover:text-[#a855f7] transition-colors" />
                                    <div className="text-xs text-muted-foreground">
                                        Drag & drop csv/xlsx or <span className="text-[#a855f7]">browse</span>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground/60 leading-tight">
                                        Account balances for the period end to validate GL data.
                                    </p>
                                </>
                            )}
                            <input
                                ref={tbInputRef}
                                type="file"
                                className="hidden"
                                accept=".csv,.xlsx,.xls,.json,.txt"
                                onChange={handleTbFileSelect}
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-[#0a0a0a] rounded-lg p-3 border border-[#1f1f1f]">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">How it works</h4>
                    <p className="text-xs text-muted-foreground">
                        Gemini parses your files automatically. We normalize your account codes and transaction types into a standard audit format. Uploading both files improves recognition accuracy.
                    </p>
                </div>

                <DialogFooter className="flex gap-4 sm:gap-4 mt-2">
                    <Button
                        variant="ghost"
                        onClick={() => { resetFiles(); onClose(); }}
                        disabled={isUploading}
                        className="text-muted-foreground hover:text-white hover:bg-[#1f1f1f]"
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleUploadSubmit}
                        disabled={!glFile || isUploading}
                        className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90 px-8"
                    >
                        {isUploading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Analyzing...
                            </>
                        ) : (
                            "Start Analysis"
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
