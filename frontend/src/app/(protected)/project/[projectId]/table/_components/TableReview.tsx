"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  FileText,
  Pencil,
  X,
  ChevronDown,
  ChevronRight,
  Plus,
  Loader2,
  Play,
  RotateCcw,
  Download,
} from "lucide-react";

interface Column {
  id: string;
  name: string;
  type: "text" | "tag" | "dropdown";
  options?: string[];
}

interface DocumentRow {
  id: string;
  name: string;
  mimeType: string;
  status: string;
  firestoreDocId?: string | null;
  analysis: {
    date?: string;
    documentType?: string;
    summary?: string;
    author?: string;
    personsMentioned?: string[];
    language?: string;
    customColumns?: Record<string, string>;
    [key: string]: any; // Allow dynamic field access
  } | null;
}

interface AnalysisJob {
  job_id: string;
  status: string;
  progress: number;
  processed_docs: number;
  total_docs: number;
}

interface TableReviewProps {
  projectTitle: string;
  projectId: string;
  vaultId: string;
}

// Template columns for Evidence Discovery
const templateColumns: Column[] = [
  { id: "date", name: "Date", type: "text" },
  { id: "documentType", name: "Document Type", type: "text" },
  { id: "summary", name: "Summary", type: "text" },
  { id: "author", name: "Author", type: "text" },
  { id: "personsMentioned", name: "Persons mentioned", type: "text" },
  { id: "language", name: "Language", type: "tag" },
];

export function TableReview({ projectTitle, projectId, vaultId }: TableReviewProps) {
  const [columns, setColumns] = useState<Column[]>([]);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const [customColumnJobs, setCustomColumnJobs] = useState<Map<string, string>>(new Map()); // jobId -> columnName
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [showCustomColumnDialog, setShowCustomColumnDialog] = useState(false);
  const [customColumnName, setCustomColumnName] = useState("");
  const [customColumnQuestion, setCustomColumnQuestion] = useState("");
  const [isRestarting, setIsRestarting] = useState(false);
  const [expandedCell, setExpandedCell] = useState<{ docId: string; columnId: string; value: string; rect: DOMRect } | null>(null);
  const { toast } = useToast();

  // Fetch documents and their analysis
  useEffect(() => {
    fetchDocuments();
  }, [vaultId]);

  // Poll for job status
  useEffect(() => {
    if (analysisJob && (analysisJob.status === "pending" || analysisJob.status === "processing")) {
      const interval = setInterval(() => {
        pollJobStatus(analysisJob.job_id);
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [analysisJob]);

  const fetchDocuments = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`/api/table/results/${vaultId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch documents");
      }

      setDocuments(data);

      // Check if any documents have analysis - if so, build columns dynamically
      const hasAnalysis = data.some((doc: DocumentRow) => doc.analysis);
      if (hasAnalysis) {
        // Start with template columns
        const dynamicColumns = [...templateColumns];
        
        // Detect custom columns from the data
        const customColumnSet = new Set<string>();
        data.forEach((doc: DocumentRow) => {
          if (doc.analysis?.customColumns) {
            Object.keys(doc.analysis.customColumns).forEach(key => {
              customColumnSet.add(key);
            });
          }
        });
        
        // Also add columns from currently processing jobs (they might not be in data yet)
        customColumnJobs.forEach((columnName) => {
          // Convert "Key Legal Issues" to "key_legal_issues"
          const fieldKey = columnName.replace(/ /g, '_').replace(/-/g, '_').toLowerCase();
          customColumnSet.add(fieldKey);
        });
        
        // Add custom columns to the list (convert field_key back to display name)
        customColumnSet.forEach(fieldKey => {
          // Convert "key_legal_issues" back to "Key Legal Issues"
          const displayName = fieldKey
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
          
          dynamicColumns.push({
            id: `custom_${fieldKey}`,
            name: displayName,
            type: "text",
          });
        });
        
        setColumns(dynamicColumns);
      }

      console.log("Fetched", data.length, "documents");
    } catch (error) {
      console.error("Failed to fetch documents:", error);
      toast({
        title: "Error",
        description: "Failed to load documents",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    try {
      const response = await fetch(`/api/table/job/${jobId}`);
      const job = await response.json();

      setAnalysisJob(job);

      if (job.status === "completed") {
        setIsAnalyzing(false);
        toast({
          title: "Analysis Complete",
          description: `Processed ${job.processed_docs} documents successfully`,
        });
        // Refresh documents to show analysis results
        fetchDocuments();
      } else if (job.status === "failed") {
        setIsAnalyzing(false);
        toast({
          title: "Analysis Failed",
          description: job.error || "An error occurred during analysis",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to poll job status:", error);
    }
  };

  const handleDiscoverEvidence = async () => {
    try {
      setIsAnalyzing(true);

      const response = await fetch("/api/table/batch-analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vault_id: vaultId,
          template: "evidence_discovery",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to start analysis");
      }

      setAnalysisJob(data);
      setColumns(templateColumns); // Show columns immediately

      toast({
        title: "Analysis Started",
        description: `Processing ${data.total_docs} documents...`,
      });
    } catch (error) {
      console.error("Failed to start analysis:", error);
      setIsAnalyzing(false);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start analysis",
        variant: "destructive",
      });
    }
  };

  const handleAddCustomColumn = async () => {
    if (!customColumnName.trim() || !customColumnQuestion.trim()) {
      toast({
        title: "Error",
        description: "Please provide both column name and question",
        variant: "destructive",
      });
      return;
    }

    try {
      setShowCustomColumnDialog(false);
      
      // Don't set isAnalyzing for custom columns, they run in parallel
      const response = await fetch("/api/table/custom-column", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vault_id: vaultId,
          column_name: customColumnName,
          question: customColumnQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to add custom column");
      }

      // Track this custom column job separately (don't interfere with Discovery)
      setCustomColumnJobs((prev) => {
        const next = new Map(prev);
        next.set(data.job_id, customColumnName);
        return next;
      });

      // Add the custom column to our columns list
      // Use field_key format for ID to match what fetchDocuments uses
      const fieldKey = customColumnName.replace(/ /g, '_').replace(/-/g, '_').toLowerCase();
      setColumns((prev) => [
        ...prev,
        {
          id: `custom_${fieldKey}`,
          name: customColumnName,
          type: "text",
        },
      ]);

      toast({
        title: "Custom Column Started",
        description: `Processing "${customColumnName}" for ${data.total_docs} documents...`,
      });

      // Start polling this specific job
      pollCustomColumnJob(data.job_id, customColumnName);

      // Reset form
      setCustomColumnName("");
      setCustomColumnQuestion("");
    } catch (error) {
      console.error("Failed to add custom column:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add custom column",
        variant: "destructive",
      });
    }
  };

  const pollCustomColumnJob = (jobId: string, columnName: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/table/job/${jobId}`);
        if (!response.ok) return;
        
        const job = await response.json();

        if (job.status === "completed") {
          clearInterval(interval);
          setCustomColumnJobs((prev) => {
            const next = new Map(prev);
            next.delete(jobId);
            return next;
          });
          toast({
            title: "Column Complete",
            description: `"${columnName}" populated for ${job.processedDocs || job.processed_docs} documents`,
          });
          fetchDocuments(); // Refresh to show new data
        } else if (job.status === "failed") {
          clearInterval(interval);
          setCustomColumnJobs((prev) => {
            const next = new Map(prev);
            next.delete(jobId);
            return next;
          });
          toast({
            title: "Column Failed",
            description: `Failed to process "${columnName}": ${job.error || "Unknown error"}`,
            variant: "destructive",
          });
        }
      } catch (error) {
        console.error("Failed to poll custom column job:", error);
      }
    }, 3000);
  };

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleRestart = async () => {
    if (!confirm("Are you sure? This will delete all analysis data and reset the table.")) {
      return;
    }

    try {
      setIsRestarting(true);

      // Delete analysis results from backend
      const response = await fetch(`/api/table/results/${vaultId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete analysis results");
      }

      // Clear columns and refresh documents
      setColumns([]);
      await fetchDocuments();

      toast({
        title: "Table Reset",
        description: "All analysis data has been cleared",
      });
    } catch (error) {
      console.error("Failed to restart:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to restart",
        variant: "destructive",
      });
    } finally {
      setIsRestarting(false);
    }
  };

  const handleExportCSV = () => {
    // Create CSV header
    const headers = ["Document", ...columns.map(col => col.name)];

    // Create CSV rows
    const rows = documents.map(doc => {
      const row = [doc.name];
      columns.forEach(column => {
        const value = getCellValue(doc, column.id);
        // Escape quotes and wrap in quotes if contains comma or quote
        const escaped = value.includes(',') || value.includes('"') || value.includes('\n')
          ? `"${value.replace(/"/g, '""')}"`
          : value;
        row.push(escaped);
      });
      return row.join(',');
    });

    // Combine header and rows
    const csv = [headers.join(','), ...rows].join('\n');

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${projectTitle}_analysis_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast({
      title: "Export Complete",
      description: "CSV file has been downloaded",
    });
  };

  const handleCellClick = (event: React.MouseEvent<HTMLDivElement>, docId: string, columnId: string, value: string) => {
    // Don't expand for short values
    if (value === "---" || value === "Unknown" || value.length < 30) return;

    const rect = event.currentTarget.getBoundingClientRect();
    setExpandedCell({ docId, columnId, value, rect });
  };

  const getCellValue = (doc: DocumentRow, columnId: string) => {
    if (!doc.analysis) return "---";

    if (columnId.startsWith("custom_")) {
      // Convert column name to field key (same as backend logic)
      const customKey = columnId.replace("custom_", "").replace(/ /g, "_").replace(/-/g, "_").toLowerCase();
      return doc.analysis.customColumns?.[customKey] || "---";
    }

    switch (columnId) {
      case "date":
        return doc.analysis.date || "Unknown";
      case "documentType":
        return doc.analysis.documentType || "Unknown";
      case "summary":
        return doc.analysis.summary || "---";
      case "author":
        return doc.analysis.author || "Unknown";
      case "personsMentioned":
        return doc.analysis.personsMentioned?.join(", ") || "---";
      case "language":
        return doc.analysis.language || "Unknown";
      default:
        return "---";
    }
  };

  return (
    <>
      <div className="flex h-[calc(100vh-4rem)] -m-4 bg-background relative">
        {/* Main Table Area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Header */}
          <div className="border-b bg-card flex-shrink-0 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold text-foreground">
                  Tabular Review #{projectTitle}
                </h1>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="default" 
                  size="sm"
                  onClick={handleDiscoverEvidence}
                  disabled={isAnalyzing || isRestarting || documents.length === 0}
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing... {analysisJob?.progress || 0}%
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Discover
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCustomColumnDialog(true)}
                  disabled={isAnalyzing || isRestarting || documents.length === 0 || columns.length === 0}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add column
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRestart}
                  disabled={isAnalyzing || isRestarting || columns.length === 0}
                >
                  {isRestarting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Restarting...
                    </>
                  ) : (
                    <>
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Restart
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportCSV}
                  disabled={columns.length === 0 || documents.length === 0}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading documents...</p>
              </div>
            </div>
          ) : documents.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-md">
                <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No Documents</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload documents to your vault to start analyzing them.
                </p>
                <Button variant="default">Upload Documents</Button>
              </div>
            </div>
          ) : (
            /* Table */
            <div className="flex-1 overflow-auto">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-card border-b z-10">
                  <tr>
                    <th className="w-8 p-2"></th>
                    <th className="text-left p-3 font-semibold text-sm text-muted-foreground border-r">
                      Document
                    </th>
                    {columns.map((column) => (
                      <th
                        key={column.id}
                        className="text-left p-3 font-semibold text-sm text-muted-foreground border-r"
                      >
                        {column.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc, index) => (
                    <tr
                      key={doc.id}
                      className="border-b hover:bg-muted/30 transition-colors"
                    >
                      <td className="p-2 text-center text-xs text-muted-foreground">
                        {index + 1}
                      </td>
                      <td className="p-3 border-r">
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5"
                            onClick={() => toggleRow(doc.id)}
                          >
                            {expandedRows.has(doc.id) ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                          </Button>
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{doc.name}</span>
                          {doc.status === "pending" && (
                            <span className="text-xs text-amber-500">Processing...</span>
                          )}
                        </div>
                      </td>
                      {columns.map((column) => {
                        const value = getCellValue(doc, column.id);
                        const isLongText = value.length > 30 && value !== "---" && value !== "Unknown";

                        return (
                          <td key={column.id} className="p-3 border-r align-top">
                            <div className="text-sm text-foreground">
                              {column.id === "language" ? (
                                <span className="inline-block px-2 py-0.5 bg-orange-500/20 text-orange-600 dark:text-orange-400 rounded text-xs font-medium">
                                  {value}
                                </span>
                              ) : (
                                <div
                                  className={`max-w-md line-clamp-3 ${isLongText ? 'cursor-pointer hover:bg-muted/50 rounded p-1 -m-1 transition-colors' : ''}`}
                                  onClick={(e) => isLongText && handleCellClick(e, doc.id, column.id, value)}
                                >
                                  {value}
                                </div>
                              )}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Custom Column Dialog */}
      <Dialog open={showCustomColumnDialog} onOpenChange={setShowCustomColumnDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Custom Column</DialogTitle>
            <DialogDescription>
              Create a custom column by asking a question. AI will answer this question for each document.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Column Name</label>
              <Input
                placeholder="e.g., Compliance Issues"
                value={customColumnName}
                onChange={(e) => setCustomColumnName(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Question</label>
              <Textarea
                placeholder="e.g., What compliance issues are mentioned in this document?"
                value={customColumnQuestion}
                onChange={(e) => setCustomColumnQuestion(e.target.value)}
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCustomColumnDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddCustomColumn}>
              <Play className="h-4 w-4 mr-2" />
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Expanded Cell Overlay */}
      {expandedCell && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedCell(null)}
        >
          <div
            className="bg-card border rounded-lg shadow-lg max-w-2xl w-full max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">
                  {columns.find(c => c.id === expandedCell.columnId)?.name || "Cell Content"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {documents.find(d => d.id === expandedCell.docId)?.name}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setExpandedCell(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <p className="text-sm whitespace-pre-wrap">{expandedCell.value}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
