"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Send, User, Bot, Loader2, MoreVertical, Pencil, X, FileText, Search, FileSearch, GitCompare, CheckCircle } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ExplorerPanel } from "@/components/global/explorer-panel";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import dynamic from 'next/dynamic';

// Dynamically import DocumentViewer to avoid SSR issues with PDF.js
const DocumentViewer = dynamic(() => import('@/components/document-viewer/DocumentViewer'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-full"><Loader2 className="h-6 w-6 animate-spin" /></div>
});

interface Project {
  id: string;
  title: string;
  description?: string | null;
  createdAt: Date;
  Vault?: {
    id: string;
    name: string;
  };
}

interface Folder {
  id: string;
  name: string;
  path: string;
  depth: number;
}

interface Document {
  id: string;
  name: string;
  originalName: string;
  folderId?: string;
  status: string;
  uploadedAt: Date | string;
  size: bigint | string;
  mimeType: string;
  path: string;
}

interface Vault {
  id: string;
  name: string;
  Folders: Folder[];
  Documents: Document[];
}

interface ChatInterfaceProps {
  project: Project;
  vault: Vault | null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  references?: Reference[];
}

interface Reference {
  id: string;
  documentId: string;
  documentName: string;
  pageNumber?: number;
  snippet: string;
}

// Mock conversation data
const mockMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    content: "Hello! I'm your AI assistant. I can help you analyze documents, answer questions about your project, and provide insights. How can I assist you today?",
    timestamp: new Date(Date.now() - 3600000),
  },
  {
    id: "2",
    role: "user",
    content: "Can you summarize the main findings from the uploaded documents?",
    timestamp: new Date(Date.now() - 3500000),
  },
  {
    id: "3",
    role: "assistant",
    content: "Based on the documents in your vault, here are the key findings:\n\n1. **Project Overview**: The documents contain evidence and documentation related to your project [1].\n\n2. **Document Organization**: Files are organized into folders for better structure and accessibility [2].\n\n3. **Processing Status**: All documents have been successfully processed and are ready for analysis [3].\n\nWould you like me to dive deeper into any specific document or topic?",
    timestamp: new Date(Date.now() - 3400000),
    references: [
      {
        id: "ref-1",
        documentId: "doc-1",
        documentName: "Project_Overview.pdf",
        pageNumber: 1,
        snippet: "This project contains comprehensive evidence and documentation related to legal proceedings, including case files, witness statements, and expert testimonies.",
      },
      {
        id: "ref-2",
        documentId: "doc-2",
        documentName: "Organization_Guide.pdf",
        pageNumber: 3,
        snippet: "Files should be organized into folders based on document type, date, and relevance to ensure easy retrieval and systematic analysis.",
      },
      {
        id: "ref-3",
        documentId: "doc-3",
        documentName: "Processing_Status.pdf",
        pageNumber: 2,
        snippet: "All documents have been successfully processed through OCR and indexed for full-text search capabilities.",
      },
    ],
  },
  {
    id: "4",
    role: "user",
    content: "What insights can you provide about the evidence folder?",
    timestamp: new Date(Date.now() - 3000000),
  },
  {
    id: "5",
    role: "assistant",
    content: "The Evidence folder contains critical documentation for your project. Here's what I can tell you:\n\n• **Document Count**: Multiple files have been uploaded and processed [1]\n• **File Types**: Various formats including documents and data files [2]\n• **Status**: All files have been successfully processed\n• **Organization**: Files are well-organized within the folder structure\n\nI can help you search through specific documents, extract information, or answer questions about the content. What would you like to know more about?",
    timestamp: new Date(Date.now() - 2900000),
    references: [
      {
        id: "ref-4",
        documentId: "doc-4",
        documentName: "Evidence_Inventory.pdf",
        pageNumber: 5,
        snippet: "A total of 47 documents have been uploaded to the Evidence folder, including witness statements, photographs, and expert reports.",
      },
      {
        id: "ref-5",
        documentId: "doc-5",
        documentName: "File_Types_Summary.pdf",
        pageNumber: 1,
        snippet: "The evidence collection includes PDF documents (65%), images (25%), spreadsheets (7%), and other file types (3%).",
      },
    ],
  },
];

export default function ChatInterface({ project, vault }: ChatInterfaceProps) {
  const router = useRouter();
  const { toast } = useToast();

  // Chat state - start empty like ChatGPT
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [inputHeight, setInputHeight] = useState(56);

  // Rename dialog
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");

  // Function to render content with clickable references
  const renderContentWithReferences = (content: string, references?: Reference[]) => {
    if (!references || references.length === 0) {
      return (
        <ReactMarkdown
          components={{
            p: ({node, ...props}) => <p className="mb-2 whitespace-pre-wrap" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc ml-4 space-y-1 mb-2" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal ml-4 space-y-1 mb-2" {...props} />,
            li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
            strong: ({node, ...props}) => <strong className="font-semibold text-foreground" {...props} />,
            em: ({node, ...props}) => <em className="italic" {...props} />,
            code: ({node, ...props}) => <code className="bg-muted px-1 py-0.5 rounded text-xs" {...props} />,
            h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-2 mt-4" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-lg font-semibold mb-2 mt-3" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-base font-semibold mb-1 mt-2" {...props} />,
          }}
        >
          {content}
        </ReactMarkdown>
      );
    }

    // Custom component to handle text nodes with citations
    const CitationText = ({ children }: { children: React.ReactNode }): JSX.Element => {
      // Handle non-string children
      if (typeof children !== 'string') {
        // If it's an array, process each element
        if (Array.isArray(children)) {
          return <>{children.map((child, i) => <CitationText key={i}>{child}</CitationText>)}</>;
        }
        // Return as-is if not a string or array
        return <>{children}</>;
      }

      // Split by citation patterns
      const parts = children.split(/(\[\d+(?:,\s*\d+)*\])/g);

      return (
        <>
          {parts.map((part, index) => {
            const match = part.match(/\[(\d+(?:,\s*\d+)*)\]/);
            if (match) {
              // Parse citation numbers
              const numbers = match[1].split(',').map((n: string) => parseInt(n.trim()));
              return (
                <span key={index} className="inline-flex gap-1 items-baseline mx-0.5">
                  {numbers.map((refNumber, i) => {
                    const reference = references[refNumber - 1];
                    if (reference) {
                      return (
                        <Tooltip key={`${index}-${i}`} delayDuration={200}>
                          <TooltipTrigger asChild>
                            <button
                              className="inline-flex items-center justify-center h-5 w-5 text-xs font-medium bg-yellow-500/15 hover:bg-yellow-500/25 text-yellow-700 dark:text-yellow-400 border border-yellow-500/30 rounded-md transition-colors flex-shrink-0 cursor-pointer"
                            >
                              {refNumber}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent
                            side="top"
                            className="max-w-sm p-0 bg-popover text-popover-foreground border shadow-lg"
                          >
                            <div className="space-y-0">
                              <div className="px-3 py-2 border-b bg-muted/50">
                                <p className="text-xs font-semibold text-foreground">
                                  {reference.documentName}
                                </p>
                                {reference.pageNumber && (
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    Page {reference.pageNumber}
                                  </p>
                                )}
                              </div>
                              <div className="px-3 py-2">
                                <p className="text-xs leading-relaxed text-muted-foreground">
                                  {reference.snippet?.substring(0, 200)}
                                  {reference.snippet && reference.snippet.length > 200 && '...'}
                                </p>
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      );
                    }
                    return null;
                  })}
                </span>
              );
            }
            // Return plain text
            return <span key={index}>{part}</span>;
          })}
        </>
      );
    };

    // Render markdown with custom text component that handles citations
    return (
      <ReactMarkdown
        components={{
          p: ({node, children, ...props}) => (
            <p className="mb-2 whitespace-pre-wrap" {...props}>
              <CitationText>{children}</CitationText>
            </p>
          ),
          ul: ({node, ...props}) => <ul className="list-disc ml-4 space-y-1 mb-2" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal ml-4 space-y-1 mb-2" {...props} />,
          li: ({node, children, ...props}) => (
            <li className="leading-relaxed" {...props}>
              <CitationText>{children}</CitationText>
            </li>
          ),
          strong: ({node, children, ...props}) => (
            <strong className="font-semibold text-foreground" {...props}>
              <CitationText>{children}</CitationText>
            </strong>
          ),
          em: ({node, children, ...props}) => (
            <em className="italic" {...props}>
              <CitationText>{children}</CitationText>
            </em>
          ),
          code: ({node, ...props}) => <code className="bg-muted px-1 py-0.5 rounded text-xs" {...props} />,
          h1: ({node, children, ...props}) => (
            <h1 className="text-xl font-bold mb-2 mt-4" {...props}>
              <CitationText>{children}</CitationText>
            </h1>
          ),
          h2: ({node, children, ...props}) => (
            <h2 className="text-lg font-semibold mb-2 mt-3" {...props}>
              <CitationText>{children}</CitationText>
            </h2>
          ),
          h3: ({node, children, ...props}) => (
            <h3 className="text-base font-semibold mb-1 mt-2" {...props}>
              <CitationText>{children}</CitationText>
            </h3>
          ),
          // Handle text nodes directly
          text: ({node, ...props}: any) => {
            const value = props.value || props.children;
            return <CitationText>{value}</CitationText>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  const documents = vault?.Documents || [];

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const query = inputValue;
    setInputValue("");
    setIsTyping(true);

    try {
      // Call backend Q&A API
      const response = await fetch("/api/qa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          project_id: project.id,
          k: 5, // Retrieve top 5 chunks
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      // Fix citation numbering to be sequential 1, 2, 3...
      // LLM uses 1-based citation numbers, but they may not be sequential or may have gaps
      // We need to map them to sequential 1, 2, 3... and reorder references accordingly
      
      let processedContent = data.answer;
      
      // Find all citation patterns: [4], [4, 5], etc.
      const citationPattern = /\[(\d+(?:,\s*\d+)*)\]/g;
      const matches = [...data.answer.matchAll(citationPattern)];
      
      // Create mapping of old numbers to new sequential numbers
      // Track order of first appearance
      const citationMap = new Map<number, number>();
      const citationOrder: number[] = [];
      let nextNumber = 1;
      
      // Process matches to build the map
      for (const match of matches) {
        const numbers = match[1].split(',').map((n: string) => parseInt(n.trim()));
        for (const oldNum of numbers) {
          if (!citationMap.has(oldNum)) {
            citationMap.set(oldNum, nextNumber++);
            citationOrder.push(oldNum);
          }
        }
      }
      
      // Replace all citations with new sequential numbers
      // IMPORTANT: Deduplicate and sort WITHIN each bracket
      processedContent = processedContent.replace(citationPattern, (match: string, numsStr: string) => {
        const oldNumbers = numsStr.split(',').map((n: string) => parseInt(n.trim()));
        // Deduplicate within this bracket
        const uniqueOldNumbers = [...new Set(oldNumbers)];
        // Map to new numbers
        const newNumbers = uniqueOldNumbers
          .map((oldNum: number) => citationMap.get(oldNum))
          .filter((n: number | undefined): n is number => n !== undefined);
        // Sort ascending
        newNumbers.sort((a, b) => a - b);
        return `[${newNumbers.join(', ')}]`;
      });
      
      // Reorder references to match new sequential numbering
      // Backend citations use 1-based indexing (citation [1] = data.citations[0])
      const reorderedReferences: Reference[] = citationOrder.map((oldNum, index) => {
        const backendIndex = oldNum - 1; // Convert 1-based to 0-based
        const cite = data.citations[backendIndex];
        if (!cite) {
          console.warn(`Missing citation for number ${oldNum}`);
          return null;
        }
        return {
          id: `ref-${Date.now()}-${index}`,
          documentId: cite.doc_id || cite.elastic_doc_id,
          documentName: cite.doc_title,
          pageNumber: cite.page,
          snippet: cite.snippet,
        };
      }).filter(ref => ref !== null) as Reference[];
      
      // Debug logging (stored in localStorage for Debug panel)
      console.log("📊 Citation Processing: ", reorderedReferences.length, "references");

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: processedContent, // Use processed content with sequential citations
        timestamp: new Date(),
        references: reorderedReferences.length > 0 ? reorderedReferences : undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      // Store debug info in localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('lastQuery', query);
        localStorage.setItem('lastResponse', JSON.stringify({
          answer: data.answer,
          citationsCount: data.citations?.length || 0,
          stats: data.stats || {},
        }));
        localStorage.setItem('citationMap', JSON.stringify(Array.from(citationMap.entries())));
        
        // Store detailed citation/reference mapping for debugging
        localStorage.setItem('lastReferences', JSON.stringify(
          reorderedReferences.map((ref, idx) => ({
            citationNumber: idx + 1,
            documentName: ref.documentName,
            pageNumber: ref.pageNumber,
            snippetPreview: ref.snippet?.substring(0, 100) + (ref.snippet && ref.snippet.length > 100 ? '...' : ''),
            fullSnippet: ref.snippet
          }))
        ));
        
        // Store raw backend citations for comparison
        localStorage.setItem('backendCitations', JSON.stringify(
          data.citations?.map((cite: any, idx: number) => ({
            originalNumber: idx + 1,
            doc_title: cite.doc_title,
            page: cite.page,
            snippetPreview: cite.snippet?.substring(0, 100) + (cite.snippet && cite.snippet.length > 100 ? '...' : ''),
          })) || []
        ));
        
        // Add to processing log (keep last 10 entries)
        const existingLog = JSON.parse(localStorage.getItem('processingLog') || '[]');
        const newLog = [
          ...existingLog,
          {
            timestamp: new Date().toISOString(),
            query: query,
            citationsFound: data.citations?.length || 0,
            referencesReordered: reorderedReferences.length,
            processingTimeMs: data.stats?.total_time_ms || 0,
          }
        ].slice(-10); // Keep only last 10
        localStorage.setItem('processingLog', JSON.stringify(newLog));
      }
    } catch (error) {
      console.error("Q&A API error:", error);
      
      // Store error in localStorage
      if (typeof window !== 'undefined') {
        const errorInfo = {
          timestamp: new Date().toISOString(),
          error: error instanceof Error ? error.message : String(error),
          query: query,
        };
        localStorage.setItem('lastError', JSON.stringify(errorInfo));
      }
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error while processing your question. Please ensure the backend is running and try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      
      toast({
        title: "Error",
        description: "Failed to get answer from AI",
        variant: "destructive",
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRename = async () => {
    if (!newName.trim()) return;

    try {
      const { renameProject } = await import("@/actions/project");
      const result = await renameProject(project.id, newName.trim());
      if (result.status === 200) {
        toast({ title: "Success", description: "Project renamed successfully" });
        router.refresh();
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to rename",
        variant: "destructive",
      });
    } finally {
      setRenameDialogOpen(false);
      setNewName("");
    }
  };

  // Check if we have any messages
  const hasConversation = messages.length > 0;

  return (
    <TooltipProvider>
      <div className="flex h-[calc(100vh-4rem)] -m-4 bg-background relative">
        {/* Explorer Panel - Left Side */}
        <div className="w-64 border-r flex-shrink-0">
          <ExplorerPanel vault={vault} projectId={project.id} />
        </div>

      {/* Main Chat Area - Right Side */}
      <div className="flex flex-col flex-1 min-h-0 relative">
        {/* Header - Only show when there's conversation */}
        {hasConversation && (
          <div className="border-b bg-card flex-shrink-0">
            <div className="flex items-center justify-between p-4 max-w-4xl mx-auto">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold text-foreground">{project.title}</h1>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setNewName(project.title);
                        setRenameDialogOpen(true);
                      }}
                    >
                      <Pencil className="mr-2 h-4 w-4" />
                      Rename Project
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
        )}

        {/* Chat Messages Area - Only show when there's conversation */}
        {hasConversation ? (
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
              {messages.map((message) => (
                <div key={message.id}>
                  <div
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {message.role === "user" ? (
                      <div className="rounded-3xl px-4 py-3 max-w-[70%] bg-muted text-foreground">
                        <div className="whitespace-pre-wrap break-words">
                          {message.content}
                        </div>
                        <div className="text-xs mt-2 text-muted-foreground">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="w-full">
                        <div className="text-foreground py-2 max-w-3xl prose dark:prose-invert prose-sm max-w-none">
                          {renderContentWithReferences(message.content, message.references)}
                        </div>
                        <div className="text-xs mt-2 text-muted-foreground">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex justify-end">
                  <div className="w-full py-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          // Empty state - centered like ChatGPT
          <div className="flex-1 flex items-center justify-center">
            <div className="max-w-2xl px-6 text-center">
              <h1 className="text-3xl font-semibold text-foreground mb-4">
                {project.title === "Untitled" ? "Clause Search" : project.title}
              </h1>
              <p className="text-muted-foreground mb-8">
                Ask me anything about your documents. I can help you find information, analyze content, and answer questions with citations.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div className="p-3 bg-muted/50 rounded-lg text-left">
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-primary" />
                    <p className="text-foreground font-medium">Search documents</p>
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">Find specific information across all files</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg text-left">
                  <div className="flex items-center gap-2">
                    <FileSearch className="h-4 w-4 text-primary" />
                    <p className="text-foreground font-medium">Analyze content</p>
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">Get insights and summaries</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg text-left">
                  <div className="flex items-center gap-2">
                    <GitCompare className="h-4 w-4 text-primary" />
                    <p className="text-foreground font-medium">Compare information</p>
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">Cross-reference multiple documents</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg text-left">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-primary" />
                    <p className="text-foreground font-medium">Get citations</p>
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">Every answer includes sources</p>
                </div>
              </div>
            </div>
          </div>
        )}

      {/* Input Area - Always visible and fixed */}
      <div className="border-t bg-card flex-shrink-0">
        <div className="max-w-4xl mx-auto p-4">
          <div className="relative">
            <Textarea
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                // Auto-resize
                e.target.style.height = 'auto';
                const newHeight = e.target.scrollHeight;
                e.target.style.height = newHeight + 'px';
                setInputHeight(newHeight);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Message your AI assistant..."
              className={`w-full min-h-[56px] max-h-[200px] pl-4 pr-12 py-4 resize-none bg-background border border-border focus:outline-none focus:ring-2 focus:ring-ring overflow-y-auto ${
                inputHeight > 80 ? 'rounded-3xl' : 'rounded-full'
              }`}
              rows={1}
              style={{ height: '56px' }}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isTyping}
              size="icon"
              className="absolute right-2 bottom-2 h-10 w-10 rounded-full"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center justify-center mt-2 text-xs text-muted-foreground">
            <span>Press Enter to send, Shift + Enter for new line</span>
          </div>
        </div>
      </div>

        {/* Rename Dialog */}
        <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rename Project</DialogTitle>
              <DialogDescription>
                Enter a new name for this project.
              </DialogDescription>
            </DialogHeader>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New name"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleRename();
                }
              }}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleRename}>Rename</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
    </TooltipProvider>
  );
}
