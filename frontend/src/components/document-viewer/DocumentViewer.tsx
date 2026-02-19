"use client";

import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { FileText, ZoomIn, ZoomOut, Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// Configure PDF.js worker with fallback
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
}

interface DocumentViewerProps {
  documentName: string;
  documentId: string;
  pageNumber?: number;
  snippet?: string;
  className?: string;
  mimeType?: string;
}

export default function DocumentViewer({
  documentName,
  documentId,
  pageNumber = 1,
  snippet,
  className,
  mimeType,
}: DocumentViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(pageNumber);
  const [scale, setScale] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string>('');
  const [documentInfo, setDocumentInfo] = useState<any>(null);
  
  const isPdf = mimeType?.includes('pdf') || documentName.endsWith('.pdf');
  const isText = mimeType?.includes('text') || documentName.endsWith('.txt');

  // Mock document URL - in production, fetch from GCS
  const documentUrl = `/api/documents/${documentId}`;

  useEffect(() => {
    // Store document info in localStorage for debugging
    if (typeof window !== 'undefined') {
      const docInfo = {
        documentId,
        documentName,
        mimeType,
        isPdf,
        isText,
        pageNumber,
        timestamp: new Date().toISOString(),
      };
      localStorage.setItem('lastDocumentViewed', JSON.stringify(docInfo));
      setDocumentInfo(docInfo);
      console.log('[DocumentViewer] Loading document:', docInfo);
    }
    
    if (isText) {
      // Fetch text file content
      fetchTextContent();
    } else if (isPdf) {
      // Check if document is available
      checkDocumentAvailability();
    }
  }, [documentId, isText, isPdf]);

  const checkDocumentAvailability = async () => {
    try {
      console.log('[DocumentViewer] Checking document availability:', documentUrl);
      const response = await fetch(documentUrl, { method: 'HEAD' });
      
      if (!response.ok) {
        // Try GET to see if it's a JSON error response
        const getResponse = await fetch(documentUrl);
        if (getResponse.headers.get('Content-Type')?.includes('application/json')) {
          const errorData = await getResponse.json();
          console.log('[DocumentViewer] Document not available:', errorData);
          setError(errorData.message || errorData.error || 'Document not available');
          setLoading(false);
          
          // Store error in localStorage
          if (typeof window !== 'undefined') {
            localStorage.setItem('lastDocumentError', JSON.stringify({
              ...errorData,
              timestamp: new Date().toISOString(),
            }));
          }
        }
      }
    } catch (err) {
      console.warn('[DocumentViewer] Pre-check failed, will try loading anyway:', err);
    }
  };
  
  const fetchTextContent = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to fetch from API
      try {
        const response = await fetch(documentUrl);
        
        // Check if response is JSON (error response)
        const contentType = response.headers.get('Content-Type');
        if (contentType?.includes('application/json')) {
          const errorData = await response.json();
          console.log('[DocumentViewer] Document not available:', errorData);
          setError(errorData.message || errorData.error || 'Document not available');
          setLoading(false);
          return;
        }
        
        if (response.ok) {
          const content = await response.text();
          setTextContent(content);
          setLoading(false);
          return;
        }
      } catch (fetchError) {
        console.warn('[DocumentViewer] Failed to fetch text from API:', fetchError);
      }
      
      // Fallback to mock content for demo
      const mockContent = snippet 
        ? `${snippet}\n\n[Full document content would be fetched from GCS here]\n\nThis is where the full text file would be displayed with proper formatting and line numbers.`
        : '[Full document content would be loaded here]\n\nUse the citation snippet above to see the relevant text.';
      
      setTextContent(mockContent);
      setLoading(false);
    } catch (err) {
      console.error('[DocumentViewer] Error loading text file:', err);
      setError(err instanceof Error ? err.message : 'Failed to load text file');
      setLoading(false);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    console.error('Error details:', {
      message: error.message,
      name: error.name,
      stack: error.stack,
    });
    
    // Provide more helpful error messages
    let errorMessage = 'Failed to load PDF document';
    if (error.message.includes('404') || error.message.includes('Not Found')) {
      errorMessage = 'Document not found. The file may have been moved or deleted.';
    } else if (error.message.includes('network') || error.message.includes('fetch')) {
      errorMessage = 'Network error. Please check your connection and try again.';
    } else if (error.message.includes('Invalid PDF')) {
      errorMessage = 'Invalid PDF file. The document may be corrupted.';
    }
    
    setError(errorMessage);
    setLoading(false);
  };

  const highlightText = (text: string, highlight: string) => {
    if (!highlight) return text;
    
    const parts = text.split(new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, index) => {
      if (part.toLowerCase() === highlight.toLowerCase()) {
        return (
          <mark key={index} className="bg-yellow-300 dark:bg-yellow-600">
            {part}
          </mark>
        );
      }
      return part;
    });
  };

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center h-full min-h-[400px]", className)}>
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center justify-center h-full min-h-[400px] p-4", className)}>
        <div className="text-center max-w-md">
          <FileText className="h-12 w-12 mx-auto mb-3 text-amber-500 opacity-50" />
          <h3 className="text-sm font-semibold text-foreground mb-2">Document Preview Unavailable</h3>
          <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{error}</p>
          
          <div className="bg-muted/50 rounded-lg p-3 mb-4 text-left">
            <p className="text-xs text-muted-foreground mb-2">
              <strong className="text-foreground">ℹ️ Note:</strong> The cited text is shown in the yellow banner above.
            </p>
            <p className="text-xs text-muted-foreground">
              Full document preview requires backend integration with Google Cloud Storage.
            </p>
          </div>
          
          {snippet && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900 rounded-lg p-3 text-left mb-4">
              <p className="text-[10px] font-semibold text-yellow-900 dark:text-yellow-200 mb-1">
                📄 Cited Text:
              </p>
              <p className="text-xs text-yellow-800 dark:text-yellow-300 leading-relaxed">
                {snippet.substring(0, 300)}{snippet.length > 300 && '...'}
              </p>
            </div>
          )}
          
          <Button
            onClick={() => {
              setError(null);
              setLoading(true);
              if (isText) {
                fetchTextContent();
              } else {
                checkDocumentAvailability();
              }
            }}
            size="sm"
            variant="outline"
            className="text-xs"
          >
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 border-b bg-card">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="text-xs font-medium truncate max-w-[150px]">
            {documentName}
          </span>
          {isPdf && numPages > 0 && (
            <span className="text-[10px] text-muted-foreground">
              Page {currentPage} of {numPages}
            </span>
          )}
        </div>
        
        {isPdf && (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
            >
              <ZoomOut className="h-3 w-3" />
            </Button>
            <span className="text-[10px] text-muted-foreground min-w-[40px] text-center">
              {Math.round(scale * 100)}%
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setScale(s => Math.min(2.0, s + 0.1))}
            >
              <ZoomIn className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      {/* Document Content */}
      <div className="flex-1 overflow-auto bg-muted/20">
        {isPdf ? (
          // PDF Viewer
          <div className="p-4 flex justify-center">
            <div className="bg-white shadow-lg">
              <Document
                file={documentUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                }
              >
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />
              </Document>
            </div>
          </div>
        ) : (
          // Text Viewer with Highlighting
          <div className="p-4">
            <div className="bg-background border rounded-lg p-4 font-mono text-xs leading-relaxed">
              <pre className="whitespace-pre-wrap break-words">
                {snippet ? highlightText(textContent, snippet.substring(0, 100)) : textContent}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Page Navigation for PDFs */}
      {isPdf && numPages > 1 && (
        <div className="flex items-center justify-center gap-2 p-2 border-t bg-card">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="h-7 text-xs"
          >
            Previous
          </Button>
          <span className="text-xs text-muted-foreground min-w-[80px] text-center">
            Page {currentPage} / {numPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
            disabled={currentPage === numPages}
            className="h-7 text-xs"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

