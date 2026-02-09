"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { MessageSquare, Send, X } from "lucide-react";
import { chatApi } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

interface AuditorChatProps {
  companyId?: string;
  auditId?: string;
}

export default function AuditorChat({ companyId, auditId }: AuditorChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm your AI auditor assistant. I can help explain audit findings, answer questions about GAAP compliance, and provide insights into the financial analysis. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to the bottom anchor whenever messages change
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await chatApi.send(userMessage, companyId, auditId);

      const data = response.data;
      if (data) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.message,
            citations: data.citations,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "I apologize, but I encountered an error processing your request. Please try again.",
          },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Connection error. Please ensure the backend is running.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          size="icon"
          className="fixed bottom-6 right-6 h-14 w-14 rounded-full bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90 shadow-2xl shadow-[#00d4ff]/40 z-100 transition-all hover:scale-110 animate-in fade-in slide-in-from-bottom-4 duration-700"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] bg-[#0a0a0a] border-[#1f1f1f]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-[#00d4ff]" />
            Auditor Assistant
          </SheetTitle>
        </SheetHeader>

        <div className="flex flex-col h-[calc(100vh-120px)] mt-4">
          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto pr-2"
            style={{ scrollbarWidth: "thin", scrollbarColor: "#333 transparent" }}
          >
            <div className="space-y-4 pb-2">
              {messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg text-sm ${message.role === "user"
                      ? "bg-[#00d4ff] text-black"
                      : "bg-[#1a1a1a] text-foreground"
                      }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-[#2a2a2a]">
                        <p className="text-xs opacity-70">References:</p>
                        {message.citations.map((citation, cidx) => (
                          <span
                            key={cidx}
                            className="inline-block text-xs bg-[#0a0a0a] px-2 py-0.5 rounded mr-1 mt-1"
                          >
                            {citation}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-[#1a1a1a] p-3 rounded-lg">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-[#00d4ff] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-[#00d4ff] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-[#00d4ff] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              {/* Scroll anchor -- always at the bottom */}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input */}
          <div className="flex gap-2 mt-4">
            <Input
              placeholder="Ask about findings, GAAP rules, or the audit..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              className="bg-[#1a1a1a] border-[#2a2a2a]"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2 mt-3">
            {[
              "What are the critical findings?",
              "Explain the risk score",
              "What is structuring?",
            ].map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => setInput(suggestion)}
                className="text-xs px-2 py-1 rounded bg-[#1a1a1a] hover:bg-[#2a2a2a] text-muted-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
