"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Plus,
  Upload,
  Loader2,
  FolderOpen,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useRouter } from "next/navigation";

interface ExplorerFolder {
  id: string;
  name: string;
  path: string;
  depth: number;
  children?: ExplorerFolder[];
}

interface ExplorerDocument {
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
  Folders: ExplorerFolder[];
  Documents: ExplorerDocument[];
}

interface ExplorerPanelProps {
  vault: Vault | null;
  projectId: string;
}

export function ExplorerPanel({ vault, projectId }: ExplorerPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [createFolderDialogOpen, setCreateFolderDialogOpen] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<{ id: string; name: string } | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const { toast } = useToast();
  const router = useRouter();

  if (!vault) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-muted-foreground p-4">
        <Folder className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No vault found for this project</p>
      </div>
    );
  }

  const toggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  };

  const handleOpenUploadDialog = (folderId: string, folderName: string) => {
    setSelectedFolder({ id: folderId, name: folderName });
    setUploadDialogOpen(true);
  };

  const handleOpenCreateFolderDialog = () => {
    setCreateFolderDialogOpen(true);
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;

    setIsCreatingFolder(true);

    try {
      const { createFolder } = await import("@/actions/vault");

      // Create folder at root level
      const folderPath = `/${newFolderName.trim()}`;
      const result = await createFolder(vault.id, folderPath);

      if (result.status === 201 || result.status === 200) {
        toast({
          title: "Success",
          description: `Folder "${newFolderName}" created successfully`,
        });
        router.refresh();
      } else {
        throw new Error(result.error || "Failed to create folder");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create folder",
        variant: "destructive",
      });
    } finally {
      setIsCreatingFolder(false);
      setCreateFolderDialogOpen(false);
      setNewFolderName("");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedFolder) return;

    setIsUploading(true);

    try {
      const { createDocument, updateDocumentStatus } = await import("@/actions/vault");

      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // Create document record
        const gcsPath = `${projectId}/${file.name}`;
        const docResult = await createDocument({
          vaultId: vault.id,
          folderId: selectedFolder.id,
          name: file.name.replace(/\.[^/.]+$/, ""), // Remove extension
          originalName: file.name,
          gcsPath,
          mimeType: file.type || "application/octet-stream",
          size: file.size,
        });

        // Update document status to completed
        if (docResult.status === 201 && docResult.data) {
          await updateDocumentStatus(docResult.data.id, "completed");
        }
      }

      toast({
        title: "Success",
        description: `Successfully uploaded ${files.length} file(s)`,
      });

      router.refresh();
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to upload files",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
      setUploadDialogOpen(false);
      setSelectedFolder(null);
    }
  };

  // Build folder tree structure
  const buildFolderTree = (folders: ExplorerFolder[]): ExplorerFolder[] => {
    const folderMap = new Map<string, ExplorerFolder>();
    const rootFolders: ExplorerFolder[] = [];

    // Create a map of all folders
    folders.forEach((folder) => {
      folderMap.set(folder.id, { ...folder, children: [] });
    });

    // Build the tree
    folders.forEach((folder) => {
      const folderNode = folderMap.get(folder.id)!;
      const pathParts = folder.path.split("/").filter((p) => p.length > 0);

      if (pathParts.length === 1) {
        rootFolders.push(folderNode);
      } else {
        // Find parent folder
        const parentPath = "/" + pathParts.slice(0, -1).join("/");
        const parentFolder = Array.from(folderMap.values()).find(
          (f) => f.path === parentPath
        );
        if (parentFolder) {
          parentFolder.children = parentFolder.children || [];
          parentFolder.children.push(folderNode);
        }
      }
    });

    return rootFolders;
  };

  const folderTree = buildFolderTree(vault.Folders);

  // Debug: Log vault data
  console.log('📁 ExplorerPanel Debug:', {
    vaultId: vault.id,
    foldersCount: vault.Folders.length,
    documentsCount: vault.Documents.length,
    documentsWithFolderId: vault.Documents.filter(d => d.folderId).length,
    documentsWithoutFolderId: vault.Documents.filter(d => !d.folderId).length,
    firstDocument: vault.Documents[0],
    folders: vault.Folders.map(f => ({ id: f.id, name: f.name, path: f.path })),
    documents: vault.Documents.map(d => ({ 
      id: d.id, 
      name: d.name, 
      folderId: d.folderId,
      status: d.status 
    })),
    folderTree: folderTree,
    filteredTreeCount: folderTree.length,
  });

  // Filter by search
  const filteredTree = searchQuery
    ? folderTree.filter((folder) =>
        folder.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : folderTree;

  const filteredDocuments = searchQuery
    ? vault.Documents.filter((doc) =>
        doc.originalName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : vault.Documents;

  return (
    <div className="flex flex-col h-full bg-background/95 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-card/50">
        <div className="flex items-center gap-2">
          <Folder className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Explorer</h3>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 hover:bg-primary/10 hover:text-primary transition-colors"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem
              onClick={() => handleOpenUploadDialog(vault.Folders[0]?.id || "", vault.Folders[0]?.name || "Root")}
              className="cursor-pointer"
            >
              <Upload className="mr-2 h-4 w-4" />
              Add File
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleOpenCreateFolderDialog} className="cursor-pointer">
              <Folder className="mr-2 h-4 w-4" />
              Add Folder
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Search Bar */}
      <div className="px-3 py-3 border-b bg-card/30">
        <Input
          placeholder="Search files..."
          className="h-8 text-xs bg-background/50 border-muted-foreground/20 focus-visible:ring-primary/50"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Folder Tree */}
      <ScrollArea className="flex-1">
        <div className="py-2">
          {/* Root-level documents (no folder) */}
          {filteredDocuments
            .filter((doc) => !doc.folderId || doc.folderId === null)
            .map((doc) => (
              <DocumentNode key={doc.id} document={doc} depth={0} />
            ))}

          {/* Folders */}
          {filteredTree.map((folder) => (
            <FolderNode
              key={folder.id}
              folder={folder}
              isExpanded={expandedFolders.has(folder.id)}
              onToggle={() => toggleFolder(folder.id)}
              onUpload={handleOpenUploadDialog}
              documents={filteredDocuments}
              expandedFolders={expandedFolders}
              onToggleFolder={toggleFolder}
              depth={0}
            />
          ))}

          {filteredTree.length === 0 && filteredDocuments.length === 0 && (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="rounded-full bg-muted/50 p-4 mb-3">
                {searchQuery ? (
                  <File className="h-8 w-8 text-muted-foreground/50" />
                ) : (
                  <Folder className="h-8 w-8 text-muted-foreground/50" />
                )}
              </div>
              <p className="text-xs text-muted-foreground font-medium mb-1">
                {searchQuery ? "No files found" : "No files yet"}
              </p>
              <p className="text-[11px] text-muted-foreground/70 max-w-[200px]">
                {searchQuery
                  ? "Try adjusting your search query"
                  : "Click the + button to add files or folders"}
              </p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-primary" />
              Upload Documents
            </DialogTitle>
            <DialogDescription>
              Upload files to <span className="font-semibold text-foreground">{selectedFolder?.name}</span>
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label
              htmlFor="file-upload"
              className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer bg-muted/30 hover:bg-muted/50 hover:border-primary/50 transition-all duration-200"
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {isUploading ? (
                  <>
                    <Loader2 className="h-10 w-10 animate-spin text-primary mb-3" />
                    <p className="text-sm font-medium text-foreground mb-1">Uploading files...</p>
                    <p className="text-xs text-muted-foreground">Please wait</p>
                  </>
                ) : (
                  <>
                    <div className="rounded-full bg-primary/10 p-3 mb-3">
                      <Upload className="h-6 w-6 text-primary" />
                    </div>
                    <p className="text-sm font-medium text-foreground mb-1">Click to upload</p>
                    <p className="text-xs text-muted-foreground">or drag and drop files here</p>
                  </>
                )}
              </div>
              <input
                id="file-upload"
                type="file"
                multiple
                className="hidden"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </label>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setUploadDialogOpen(false)}
              disabled={isUploading}
            >
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Folder Dialog */}
      <Dialog open={createFolderDialogOpen} onOpenChange={setCreateFolderDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Folder className="h-5 w-5 text-amber-500" />
              Create New Folder
            </DialogTitle>
            <DialogDescription>
              Enter a name for the new folder
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Input
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="e.g., Legal Documents"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isCreatingFolder && newFolderName.trim()) {
                  handleCreateFolder();
                }
              }}
              disabled={isCreatingFolder}
              className="focus-visible:ring-primary/50"
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCreateFolderDialogOpen(false);
                setNewFolderName("");
              }}
              disabled={isCreatingFolder}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateFolder}
              disabled={isCreatingFolder || !newFolderName.trim()}
            >
              {isCreatingFolder ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Folder className="mr-2 h-4 w-4" />
                  Create
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Folder Node Component
const FolderNode: React.FC<{
  folder: ExplorerFolder;
  isExpanded: boolean;
  onToggle: () => void;
  onUpload: (folderId: string, folderName: string) => void;
  documents: ExplorerDocument[];
  expandedFolders: Set<string>;
  onToggleFolder: (folderId: string) => void;
  depth: number;
}> = ({
  folder,
  isExpanded,
  onToggle,
  onUpload,
  documents,
  expandedFolders,
  onToggleFolder,
  depth,
}) => {
  const [isHovered, setIsHovered] = useState(false);

  // Get documents in this folder
  const folderDocuments = documents.filter((doc) => doc.folderId === folder.id);

  return (
    <div>
      <div
        className={cn(
          "flex items-center py-1.5 px-2 hover:bg-primary/5 cursor-pointer text-xs group rounded-md mx-1 transition-all duration-200",
          isExpanded && "bg-muted/30"
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div
          className="w-5 h-5 flex items-center justify-center mr-1 hover:bg-muted/50 rounded transition-colors"
          onClick={onToggle}
        >
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </div>
        <div className="flex-1 flex items-center min-w-0 gap-2" onClick={onToggle}>
          {isExpanded ? (
            <FolderOpen className="h-4 w-4 text-amber-500 flex-shrink-0" />
          ) : (
            <Folder className="h-4 w-4 text-amber-600 flex-shrink-0" />
          )}
          <span className="truncate text-foreground font-medium">{folder.name}</span>
          <span className="text-[10px] text-muted-foreground flex-shrink-0">
            {folderDocuments.length}
          </span>
        </div>
        {isHovered && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-primary/10 hover:text-primary"
            onClick={(e) => {
              e.stopPropagation();
              onUpload(folder.id, folder.name);
            }}
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {isExpanded && (
        <div className="mt-0.5">
          {/* Child folders */}
          {folder.children?.map((child) => (
            <FolderNode
              key={child.id}
              folder={child}
              isExpanded={expandedFolders.has(child.id)}
              onToggle={() => onToggleFolder(child.id)}
              onUpload={onUpload}
              documents={documents}
              expandedFolders={expandedFolders}
              onToggleFolder={onToggleFolder}
              depth={depth + 1}
            />
          ))}

          {/* Documents in this folder */}
          {folderDocuments.map((doc) => (
            <DocumentNode key={doc.id} document={doc} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

// Document Node Component
const DocumentNode: React.FC<{
  document: ExplorerDocument;
  depth: number;
}> = ({ document, depth }) => {
  const [isHovered, setIsHovered] = useState(false);
  const isProcessing = document.status === "processing" || document.status === "pending";
  const isCompleted = document.status === "completed" || document.status === "indexed";
  const isFailed = document.status === "failed";

  // Get file extension
  const fileExtension = document.originalName.split('.').pop()?.toUpperCase() || '';

  return (
    <div
      className="flex items-center py-1.5 px-2 hover:bg-primary/5 cursor-pointer text-xs rounded-md mx-1 transition-all duration-200 group"
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="w-5 h-5 mr-1" />
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <File className="h-4 w-4 text-blue-500 flex-shrink-0" />
        <span className="truncate text-foreground flex-1">{document.originalName}</span>
        {fileExtension && fileExtension.length <= 4 && (
          <span className="text-[9px] text-muted-foreground/60 font-mono flex-shrink-0 bg-muted/40 px-1 py-0.5 rounded">
            {fileExtension}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1 ml-2 flex-shrink-0">
        {isProcessing && (
          <div className="flex items-center gap-1 bg-amber-500/10 text-amber-600 px-1.5 py-0.5 rounded-md">
            <Loader2 className="h-3 w-3 animate-spin" title="Processing..." />
            <span className="text-[9px] font-medium">Processing</span>
          </div>
        )}
        {isCompleted && isHovered && (
          <div className="flex items-center gap-1 bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded-md">
            <CheckCircle2 className="h-3 w-3" title="Completed" />
            <span className="text-[9px] font-medium">Ready</span>
          </div>
        )}
        {isFailed && (
          <div className="flex items-center gap-1 bg-red-500/10 text-red-600 px-1.5 py-0.5 rounded-md">
            <AlertCircle className="h-3 w-3" title="Failed" />
            <span className="text-[9px] font-medium">Failed</span>
          </div>
        )}
      </div>
    </div>
  );
};
