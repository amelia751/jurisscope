"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Folder, FolderOpen, Loader2, Upload, CheckCircle, AlertCircle, Clock, MoreVertical, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
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

interface Project {
  id: string;
  title: string;
  description?: string;
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
}

interface Vault {
  id: string;
  name: string;
  Folders: Folder[];
  Documents: Document[];
}

interface ProjectViewProps {
  project: Project;
  vault: Vault | null;
}

const statusConfig = {
  pending: { icon: Clock, color: "text-yellow-500", bg: "bg-yellow-500/10", label: "Pending" },
  processing: { icon: Loader2, color: "text-blue-500", iconClass: "animate-spin", bg: "bg-blue-500/10", label: "Processing" },
  completed: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-500/10", label: "Completed" },
  failed: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-500/10", label: "Failed" },
};

export default function ProjectView({ project, vault }: ProjectViewProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  // Use documents from vault props (already fetched from backend in page.tsx)
  const [documents, setDocuments] = useState<Document[]>(vault?.Documents || []);
  
  // Update documents when vault prop changes
  useEffect(() => {
    if (vault?.Documents) {
      setDocuments(vault.Documents);
    }
  }, [vault?.Documents]);
  
  // Auto-refresh every 3 seconds if there are processing/pending documents
  useEffect(() => {
    const hasProcessingDocs = documents.some(doc => 
      doc.status === "processing" || doc.status === "pending"
    );
    
    if (hasProcessingDocs) {
      const interval = setInterval(async () => {
        // Refresh from backend API
        try {
          const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005';
          const response = await fetch(`${backendUrl}/api/documents?project_id=${project.id}`);
          if (response.ok) {
            const data = await response.json();
            const backendDocs: Document[] = (data.documents || []).map((doc: any) => ({
              id: doc.id,
              name: doc.title,
              originalName: doc.title,
              folderId: undefined,
              status: doc.status === 'indexed' ? 'completed' : doc.status,
              uploadedAt: doc.created_at,
              size: '0',
              mimeType: doc.mime || 'application/pdf',
            }));
            setDocuments(backendDocs);
          }
        } catch (error) {
          console.error('Auto-refresh failed:', error);
        }
      }, 3000); // Every 3 seconds
      
      return () => clearInterval(interval);
    }
  }, [documents, project.id]);
  
  // Rename dialogs
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<{ type: "document" | "folder" | "project"; id: string; currentName: string } | null>(null);
  const [newName, setNewName] = useState("");
  
  // Delete confirmation
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ type: "document" | "folder"; id: string; name: string } | null>(null);

  useEffect(() => {
    // Check for files to upload from sessionStorage
    const filesKey = `project-${project.id}-files`;
    const filesData = sessionStorage.getItem(filesKey);

    if (filesData && vault) {
      const files = JSON.parse(filesData);
      handleUploadFiles(files);
      sessionStorage.removeItem(filesKey);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, vault]);

  const handleUploadFiles = async (files: Array<{ name: string; path: string; size: number; type: string }>) => {
    if (!vault) {
      toast({
        title: "Error",
        description: "Vault not found for this project",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);
    const uploadedDocs: Document[] = [];
    
    // Import actions dynamically
    const { createFolder, createDocument } = await import("@/actions/vault");
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress(`Processing ${i + 1}/${files.length}: ${file.name}`);

      try {
        // Extract folder path from file path
        const pathParts = file.path.split("/").filter(p => p.length > 0);
        const fileName = pathParts[pathParts.length - 1];
        const folderParts = pathParts.slice(0, -1);
        const folderPath = folderParts.length > 0 ? "/" + folderParts.join("/") : "/Evidence";

        console.log(`Processing: ${file.name} → Folder: ${folderPath}`);
        
        // Create folder if it doesn't exist
        const folderResult = await createFolder(vault.id, folderPath);
        
        if (folderResult.status !== 200 && folderResult.status !== 201) {
          throw new Error(`Failed to create folder: ${folderResult.error}`);
        }

        const folder = folderResult.data;
        
        // Create document record (simulated GCS path for now)
        const gcsPath = `${project.id}/${fileName}`;
        const docResult = await createDocument({
          vaultId: vault.id,
          folderId: folder?.id,
          name: fileName.replace(/\.[^/.]+$/, ""), // Remove extension
          originalName: fileName,
          gcsPath,
          mimeType: file.type || "application/octet-stream",
          size: file.size,
        });
        
        // Update document status to completed (since we're not actually uploading to GCS yet)
        if (docResult.status === 201 && docResult.data) {
          const { updateDocumentStatus } = await import("@/actions/vault");
          await updateDocumentStatus(docResult.data.id, "completed");
        }

        if (docResult.status === 201 && docResult.data) {
          uploadedDocs.push(docResult.data as unknown as Document);
          console.log(`✅ Created document: ${fileName}`);
        } else {
          throw new Error(`Failed to create document: ${docResult.error}`);
        }
      } catch (error) {
        console.error(`Error processing ${file.name}:`, error);
        toast({
          title: "Upload Error",
          description: `Failed to process ${file.name}: ${error instanceof Error ? error.message : "Unknown error"}`,
          variant: "destructive",
        });
      }
    }

    setIsUploading(false);
    setUploadProgress("");
    
    if (uploadedDocs.length > 0) {
      // Update local state with new documents
      setDocuments(prev => [...prev, ...uploadedDocs]);
      
      toast({
        title: "Upload Complete",
        description: `Successfully created ${uploadedDocs.length} document(s)`,
      });

      // Refresh the page to get updated data from server
      setTimeout(() => router.refresh(), 1000);
    } else {
      toast({
        title: "Upload Failed",
        description: "No documents were created",
        variant: "destructive",
      });
    }
  };

  // Group documents by folder
  const groupedDocuments = documents.reduce((acc, doc) => {
    const folderId = doc.folderId || "root";
    if (!acc[folderId]) {
      acc[folderId] = [];
    }
    acc[folderId].push(doc);
    return acc;
  }, {} as Record<string, Document[]>);

  // Create folder map
  const folderMap = (vault?.Folders || []).reduce((acc, folder) => {
    acc[folder.id] = folder;
    return acc;
  }, {} as Record<string, Folder>);

  const formatFileSize = (bytes: bigint | string): string => {
    const numBytes = typeof bytes === 'string' ? Number(bytes) : Number(bytes);
    const kb = numBytes / 1024;
    if (kb < 1024) return `${kb.toFixed(2)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB`;
  };

  const getStatusBadge = (status: string) => {
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;
    const iconClass = 'iconClass' in config ? config.iconClass : '';

    return (
      <Badge variant="outline" className={`${config.bg} border-none`}>
        <Icon className={`w-3 h-3 mr-1 ${config.color} ${iconClass}`} />
        <span className={config.color}>{config.label}</span>
      </Badge>
    );
  };
  
  const handleRename = async () => {
    if (!renameTarget || !newName.trim()) return;
    
    try {
      if (renameTarget.type === "project") {
        const { renameProject } = await import("@/actions/project");
        const result = await renameProject(renameTarget.id, newName.trim());
        if (result.status === 200) {
          toast({ title: "Success", description: "Project renamed successfully" });
          router.refresh();
        } else {
          throw new Error(result.error);
        }
      } else if (renameTarget.type === "document") {
        const { renameDocument } = await import("@/actions/vault");
        const result = await renameDocument(renameTarget.id, newName.trim());
        if (result.status === 200) {
          setDocuments(prev => prev.map(d => d.id === renameTarget.id ? {...d, name: newName.trim()} : d));
          toast({ title: "Success", description: "Document renamed successfully" });
        } else {
          throw new Error(result.error);
        }
      } else if (renameTarget.type === "folder") {
        const { renameFolder } = await import("@/actions/vault");
        const result = await renameFolder(renameTarget.id, newName.trim());
        if (result.status === 200) {
          toast({ title: "Success", description: "Folder renamed successfully" });
          router.refresh();
        } else {
          throw new Error(result.error);
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to rename",
        variant: "destructive",
      });
    } finally {
      setRenameDialogOpen(false);
      setRenameTarget(null);
      setNewName("");
    }
  };
  
  const handleDelete = async () => {
    if (!deleteTarget) return;
    
    try {
      if (deleteTarget.type === "document") {
        const { deleteDocument } = await import("@/actions/vault");
        const result = await deleteDocument(deleteTarget.id);
        if (result.status === 200) {
          setDocuments(prev => prev.filter(d => d.id !== deleteTarget.id));
          toast({ title: "Success", description: "Document deleted successfully" });
        } else {
          throw new Error(result.error);
        }
      } else if (deleteTarget.type === "folder") {
        const { deleteFolder } = await import("@/actions/vault");
        const result = await deleteFolder(deleteTarget.id);
        if (result.status === 200) {
          toast({ title: "Success", description: "Folder deleted successfully" });
          router.refresh();
        } else {
          throw new Error(result.error);
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to delete",
        variant: "destructive",
      });
    } finally {
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    }
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-primary">{project.title}</h1>
            {project.description && (
              <p className="text-muted-foreground mt-1">{project.description}</p>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    setRenameTarget({ type: "project", id: project.id, currentName: project.title });
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

        {/* Upload Progress */}
        {isUploading && (
          <Card className="p-4 bg-blue-500/10 border-blue-500/20">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              <div>
                <p className="font-medium">Uploading files...</p>
                <p className="text-sm text-muted-foreground">{uploadProgress}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Folder className="w-8 h-8 text-amber-500" />
              <div>
                <p className="text-2xl font-bold">{vault?.Folders.length || 0}</p>
                <p className="text-sm text-muted-foreground">Folders</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{documents.length}</p>
                <p className="text-sm text-muted-foreground">Documents</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">
                  {documents.filter((d) => d.status === "completed").length}
                </p>
                <p className="text-sm text-muted-foreground">Processed</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <Clock className="w-8 h-8 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold">
                  {documents.filter((d) => d.status === "pending" || d.status === "processing").length}
                </p>
                <p className="text-sm text-muted-foreground">Pending</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Documents by Folder */}
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Documents</h2>

          {documents.length === 0 ? (
            <Card className="p-12 text-center">
              <Upload className="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium text-muted-foreground">No documents yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Upload files from the create page to get started
              </p>
            </Card>
          ) : (
            Object.entries(groupedDocuments).map(([folderId, docs]) => {
              const folder = folderId === "root" ? null : folderMap[folderId];
              const folderName = folder ? folder.path : "Root";

              return (
                <Card key={folderId} className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <FolderOpen className="w-5 h-5 text-amber-500" />
                      <h3 className="text-lg font-semibold">{folderName}</h3>
                    </div>
                    {folder && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              setRenameTarget({ type: "folder", id: folder.id, currentName: folder.name });
                              setNewName(folder.name);
                              setRenameDialogOpen(true);
                            }}
                          >
                            <Pencil className="mr-2 h-4 w-4" />
                            Rename Folder
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() => {
                              setDeleteTarget({ type: "folder", id: folder.id, name: folder.name });
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete Folder
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>

                  <div className="space-y-2">
                    {docs.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="font-medium truncate" title={doc.originalName}>
                              {doc.originalName}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {formatFileSize(doc.size)} • Uploaded{" "}
                              {new Date(doc.uploadedAt).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {getStatusBadge(doc.status)}
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => {
                                  setRenameTarget({ type: "document", id: doc.id, currentName: doc.name });
                                  setNewName(doc.name);
                                  setRenameDialogOpen(true);
                                }}
                              >
                                <Pencil className="mr-2 h-4 w-4" />
                                Rename Document
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-red-600"
                                onClick={() => {
                                  setDeleteTarget({ type: "document", id: doc.id, name: doc.originalName });
                                  setDeleteDialogOpen(true);
                                }}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete Document
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              );
            })
          )}
        </div>
        
        {/* Rename Dialog */}
        <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rename {renameTarget?.type}</DialogTitle>
              <DialogDescription>
                Enter a new name for this {renameTarget?.type}.
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

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete {deleteTarget?.type}?</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete <strong>{deleteTarget?.name}</strong>? This action
                cannot be undone.
                {deleteTarget?.type === "folder" && (
                  <p className="mt-2 text-amber-600 dark:text-amber-400">
                    ⚠️ This will also delete all documents in this folder.
                  </p>
                )}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

