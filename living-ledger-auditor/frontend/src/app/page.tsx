"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Building2, 
  Upload, 
  Play, 
  FileText, 
  Network, 
  MessageSquare,
  Shield,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  Sparkles,
  Database,
  FileUp,
  Loader2
} from "lucide-react";
import AuditorChat from "@/components/chat/AuditorChat";
import QuotaExceededModal from "@/components/ui/QuotaExceededModal";

interface Scenario {
  id: string;
  name: string;
  description: string;
  industry: string;
  expected_findings: string;
  issues: string[];
}

export default function Home() {
  const router = useRouter();
  const [companies, setCompanies] = useState<any[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [dataSource, setDataSource] = useState<string>("");
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>("acme_saas");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load scenarios on mount
  useEffect(() => {
    fetch("http://localhost:8000/api/companies/scenarios")
      .then(res => res.json())
      .then(data => setScenarios(data))
      .catch(err => console.error("Failed to load scenarios:", err));
  }, []);

  const handleGenerateCompany = async () => {
    setIsGenerating(true);
    setDataSource("generate");
    try {
      const response = await fetch("http://localhost:8000/api/companies/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          num_transactions: 50,
          issue_count: 8
        })
      });
      const data = await response.json();
      
      if (response.status === 429 || data.detail?.includes("quota")) {
        setQuotaExceeded(true);
        return;
      }
      
      setCompanies([...companies, data]);
      router.push(`/company/${data.id}`);
    } catch (error) {
      console.error("Error generating company:", error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLoadExample = async (scenarioId?: string) => {
    setIsGenerating(true);
    setDataSource("example");
    try {
      const url = scenarioId 
        ? `http://localhost:8000/api/companies/example?scenario_id=${scenarioId}`
        : "http://localhost:8000/api/companies/example";
      const response = await fetch(url, {
        method: "POST",
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error("Error loading example:", response.status, errorData);
        alert(`Failed to load scenario: ${errorData.detail || response.statusText}`);
        return;
      }
      
      const data = await response.json();
      if (!data || !data.id) {
        console.error("Invalid response - missing company ID:", data);
        alert("Failed to load scenario: Invalid response from server");
        return;
      }
      
      setCompanies([...companies, data]);
      router.push(`/company/${data.id}`);
    } catch (error) {
      console.error("Error loading example:", error);
      alert(`Failed to load scenario: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsGenerating(true);
    setDataSource("upload");
    setUploadError(null);

    const formData = new FormData();
    formData.append("company_name", file.name.replace(/\.[^/.]+$/, "")); // Remove extension
    formData.append("gl_file", file);

    try {
      const response = await fetch("http://localhost:8000/api/companies/upload-smart", {
        method: "POST",
        body: formData
      });

      if (response.status === 429) {
        setQuotaExceeded(true);
        return;
      }

      const data = await response.json();
      
      if (!response.ok) {
        setUploadError(data.detail || "Upload failed");
        return;
      }

      setCompanies([...companies, data]);
      router.push(`/company/${data.id}`);
    } catch (error) {
      console.error("Error uploading file:", error);
      setUploadError("Failed to upload file. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-[#1f1f1f] bg-[#0a0a0a]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-[#00d4ff]" />
            <span className="font-semibold text-lg tracking-tight">Living Ledger Auditor</span>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="text-[#00d4ff] border-[#00d4ff]/30">
              Powered by Gemini 3
            </Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {/* Hero Section */}
        {!selectedCompany && (
          <div className="text-center py-16">
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-[#00d4ff] to-[#8b5cf6] bg-clip-text text-transparent">
              AI-Powered Financial Audit Platform
            </h1>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto mb-8">
              Detect fraud, ensure GAAP compliance, discover hidden ownership networks. 
              Every decision is transparent, every finding is explainable.
            </p>
            
            <div className="flex flex-col items-center gap-4 mb-16">
              {/* Main Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    size="lg"
                    disabled={isGenerating}
                    className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90 min-w-[280px]"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        {dataSource === "generate" && "Generating..."}
                        {dataSource === "example" && "Loading Example..."}
                        {dataSource === "upload" && "Processing Upload..."}
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-5 w-5" />
                        Get Started
                        <ChevronDown className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center" className="w-[280px] p-0 bg-[#111111] border-[#1f1f1f]">
                  <ScrollArea className="h-[400px]">
                    <div className="p-1">
                      <DropdownMenuLabel>Choose Data Source</DropdownMenuLabel>
                      <DropdownMenuSeparator className="bg-[#1f1f1f]" />
                      
                      <DropdownMenuItem 
                        onClick={handleGenerateCompany}
                        className="cursor-pointer focus:bg-[#1f1f1f] py-3"
                      >
                        <Building2 className="mr-3 h-5 w-5 text-[#00d4ff]" />
                        <div>
                          <div className="font-medium">Generate Random Data</div>
                          <div className="text-xs text-muted-foreground">AI creates synthetic company</div>
                        </div>
                      </DropdownMenuItem>
                      
                      <DropdownMenuItem 
                        onClick={handleUploadClick}
                        className="cursor-pointer focus:bg-[#1f1f1f] py-3"
                      >
                        <FileUp className="mr-3 h-5 w-5 text-[#a855f7]" />
                        <div>
                          <div className="font-medium">Upload Your Data</div>
                          <div className="text-xs text-muted-foreground">AI normalizes your files</div>
                        </div>
                      </DropdownMenuItem>
                      
                      <DropdownMenuSeparator className="bg-[#1f1f1f]" />
                      <DropdownMenuLabel className="text-xs text-muted-foreground">Demo Scenarios</DropdownMenuLabel>
                      
                      {scenarios.length > 0 ? scenarios.map((scenario) => (
                        <DropdownMenuItem 
                          key={scenario.id}
                          onClick={() => handleLoadExample(scenario.id)}
                          className="cursor-pointer focus:bg-[#1f1f1f] py-3"
                        >
                          <Database className={`mr-3 h-5 w-5 ${
                            scenario.id === "fraud_indicators" ? "text-[#ff3366]" :
                            scenario.id === "clean_retail" ? "text-[#22c55e]" :
                            "text-[#00d4ff]"
                          }`} />
                          <div>
                            <div className="font-medium">{scenario.name}</div>
                            <div className="text-xs text-muted-foreground">{scenario.expected_findings}</div>
                          </div>
                        </DropdownMenuItem>
                      )) : (
                        <DropdownMenuItem 
                          onClick={() => handleLoadExample()}
                          className="cursor-pointer focus:bg-[#1f1f1f] py-3"
                        >
                          <Database className="mr-3 h-5 w-5 text-[#22c55e]" />
                          <div>
                            <div className="font-medium">Use Example Data</div>
                            <div className="text-xs text-muted-foreground">Fixed dataset, no AI needed</div>
                          </div>
                        </DropdownMenuItem>
                      )}
                    </div>
                  </ScrollArea>
                </DropdownMenuContent>
              </DropdownMenu>

              <input 
                ref={fileInputRef}
                type="file" 
                accept=".csv,.xlsx,.xls,.json,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />

              {uploadError && (
                <div className="bg-[#ff3366]/10 border border-[#ff3366] px-4 py-2 rounded text-sm text-[#ff3366]">
                  {uploadError}
                </div>
              )}

              <p className="text-sm text-muted-foreground max-w-md">
                <strong>Use Example Data</strong> is recommended for testing - it uses fixed data with known issues 
                and doesn't require AI API calls.
              </p>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              <FeatureCard
                icon={<AlertTriangle className="h-8 w-8 text-[#ff3366]" />}
                title="Fraud Detection"
                description="Benford's Law analysis, structuring detection, round-tripping identification, shell company indicators."
              />
              <FeatureCard
                icon={<Network className="h-8 w-8 text-[#8b5cf6]" />}
                title="Ownership Discovery"
                description="Trace beneficial owners through public registries. Build ownership graphs. Find hidden relationships."
              />
              <FeatureCard
                icon={<FileText className="h-8 w-8 text-[#00d4ff]" />}
                title="Full Auditability"
                description="Every AI decision logged. Complete reasoning chains. Regulator-ready audit trails."
              />
            </div>
          </div>
        )}

        {/* Company Dashboard */}
        {selectedCompany && (
          <div className="space-y-6">
            {/* Company Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">{selectedCompany.name}</h1>
                <p className="text-muted-foreground">
                  {selectedCompany.industry} | {selectedCompany.accounting_basis} basis | {selectedCompany.reporting_period}
                </p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" size="sm">
                  <FileText className="mr-2 h-4 w-4" />
                  View COA
                </Button>
                <Button variant="outline" size="sm">
                  <TrendingUp className="mr-2 h-4 w-4" />
                  View GL
                </Button>
                <Button className="bg-[#00d4ff] text-black hover:bg-[#00d4ff]/90" size="sm">
                  <Play className="mr-2 h-4 w-4" />
                  Run Audit
                </Button>
              </div>
            </div>

            {/* Dashboard Grid */}
            <div className="grid md:grid-cols-3 gap-6">
              <Card className="bg-[#111111] border-[#1f1f1f]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Risk Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold text-[#00d4ff]">--</div>
                  <p className="text-sm text-muted-foreground mt-1">Run audit to calculate</p>
                </CardContent>
              </Card>
              
              <Card className="bg-[#111111] border-[#1f1f1f]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Findings</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold">--</div>
                  <p className="text-sm text-muted-foreground mt-1">Pending audit</p>
                </CardContent>
              </Card>
              
              <Card className="bg-[#111111] border-[#1f1f1f]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Adjusting Entries</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-4xl font-bold">--</div>
                  <p className="text-sm text-muted-foreground mt-1">Generated after audit</p>
                </CardContent>
              </Card>
            </div>

            {/* Main Content Area */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-[#111111] border-[#1f1f1f]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-[#ff6b35]" />
                    Audit Findings
                  </CardTitle>
                  <CardDescription>Run an audit to see findings</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No audit has been run yet.</p>
                    <p className="text-sm">Click "Run Audit" to analyze this company.</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-[#111111] border-[#1f1f1f]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Network className="h-5 w-5 text-[#8b5cf6]" />
                    Ownership Network
                  </CardTitle>
                  <CardDescription>Discover beneficial owners</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-muted-foreground">
                    <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No ownership analysis yet.</p>
                    <p className="text-sm">Run ownership discovery after audit.</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* AI Reasoning Chain */}
            <Card className="bg-[#111111] border-[#1f1f1f]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-[#00d4ff]" />
                  AI Reasoning Chain
                </CardTitle>
                <CardDescription>Transparent decision-making process</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="font-mono text-sm bg-[#0a0a0a] p-4 rounded border border-[#1f1f1f]">
                  <p className="text-muted-foreground">{">"} Awaiting audit execution...</p>
                  <p className="text-muted-foreground">{">"} System ready.</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Existing Companies */}
        {companies.length > 0 && !selectedCompany && (
          <div className="mt-16">
            <h2 className="text-xl font-bold mb-4">Your Companies</h2>
            <div className="grid md:grid-cols-3 gap-4">
              {companies.map((company, index) => (
                <Card 
                  key={index}
                  className="bg-[#111111] border-[#1f1f1f] cursor-pointer hover:border-[#00d4ff]/50 transition-colors"
                  onClick={() => setSelectedCompany(company)}
                >
                  <CardHeader>
                    <CardTitle className="text-lg">{company.name}</CardTitle>
                    <CardDescription>{company.industry} | {company.reporting_period}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-[#1f1f1f] mt-16 py-8">
        <div className="container mx-auto px-6 text-center text-sm text-muted-foreground">
          <p>Living Ledger Auditor - Hackathon Demo</p>
          <p className="mt-1">This is a demonstration. Not for production use. Human judgment required.</p>
        </div>
      </footer>
      
      {/* Auditor Chat */}
      <AuditorChat />
      
      {/* Quota Exceeded Modal */}
      <QuotaExceededModal 
        open={quotaExceeded}
        onClose={() => setQuotaExceeded(false)}
        onRetry={dataSource === "generate" ? handleGenerateCompany : undefined}
      />
    </main>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <Card className="bg-[#111111] border-[#1f1f1f] hover:border-[#2a2a2a] transition-colors">
      <CardHeader>
        <div className="mb-2">{icon}</div>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground text-sm">{description}</p>
      </CardContent>
    </Card>
  );
}
