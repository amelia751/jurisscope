"use client";
import { motion } from "framer-motion";
import { containerVariants, itemVariants } from "@/lib/constants";
import { useState, useCallback } from "react";
import { CloudUpload, FileCheck2, FolderOpen } from "lucide-react";
import { useRouter } from "next/navigation";
import { useToast } from "@/hooks/use-toast";

interface CourseSelectionProps {
  onSelectOption: (option: string) => void;
}

interface FileWithPath {
  file: File;
  path: string;
}

export default function CreatePage({ onSelectOption }: CourseSelectionProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<FileWithPath[]>([]);
  const router = useRouter();
  const { toast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const items = Array.from(e.dataTransfer.items);
    const filesWithPaths: FileWithPath[] = [];
    const invalidFiles: string[] = [];
    const allowedTypes = ['.pdf', '.docx', '.doc', '.txt', '.md'];

    // Helper function to recursively read directory entries
    const readDirectory = async (entry: FileSystemDirectoryEntry): Promise<void> => {
      const reader = entry.createReader();

      return new Promise((resolve) => {
        const readEntries = () => {
          reader.readEntries(async (entries) => {
            if (entries.length === 0) {
              resolve();
              return;
            }

            for (const entry of entries) {
              if (entry.isFile) {
                const fileEntry = entry as FileSystemFileEntry;
                await new Promise<void>((resolveFile) => {
                  fileEntry.file((file) => {
                    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

                    if (allowedTypes.includes(fileExt)) {
                      filesWithPaths.push({ file, path: entry.fullPath });
                      console.log(`✅ Added from folder: ${entry.fullPath}`);
                    } else {
                      if (!file.name.startsWith('.') && file.name !== 'desktop.ini' && file.name !== 'Thumbs.db') {
                        invalidFiles.push(file.name);
                        console.log(`❌ Skipped (invalid): ${entry.fullPath}`);
                      } else {
                        console.log(`⏭️ Skipped (system): ${entry.fullPath}`);
                      }
                    }
                    resolveFile();
                  });
                });
              } else if (entry.isDirectory) {
                await readDirectory(entry as FileSystemDirectoryEntry);
              }
            }

            // Continue reading if there are more entries
            readEntries();
          });
        };

        readEntries();
      });
    };

    // Process all dropped items
    const promises: Promise<void>[] = [];

    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry();

        if (entry?.isDirectory) {
          console.log(`📁 Processing folder: ${entry.name}`);
          promises.push(readDirectory(entry as FileSystemDirectoryEntry));
        } else if (entry?.isFile) {
          const file = item.getAsFile();
          if (file) {
            const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
            if (allowedTypes.includes(fileExt)) {
              filesWithPaths.push({ file, path: file.name });
              console.log(`✅ Added file: ${file.name}`);
            } else {
              if (!file.name.startsWith('.') && file.name !== 'desktop.ini' && file.name !== 'Thumbs.db') {
                invalidFiles.push(file.name);
                console.log(`❌ Skipped (invalid): ${file.name}`);
              }
            }
          }
        }
      }
    }

    // Wait for all directory traversals to complete
    await Promise.all(promises);

    console.log(`✅ Total valid files: ${filesWithPaths.length}, ❌ Invalid files: ${invalidFiles.length}`);

    if (filesWithPaths.length > 0) {
      setUploadedFiles(prev => [...prev, ...filesWithPaths]);
      toast({
        title: "Files uploaded",
        description: `${filesWithPaths.length} file(s) added successfully`,
      });
    } else if (invalidFiles.length > 0 || items.length > 0) {
      toast({
        title: "No valid files found",
        description: "No PDF, DOCX, DOC, TXT, or MD files were found",
        variant: "destructive",
      });
    }

    if (invalidFiles.length > 0) {
      toast({
        title: "Some files skipped",
        description: `${invalidFiles.length} unsupported file(s) skipped - Only PDF, DOCX, DOC, TXT, and MD files are supported`,
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const allFiles = Array.from(e.target.files || []);
    const filesWithPaths: FileWithPath[] = [];
    const invalidFiles: string[] = [];
    const allowedTypes = ['.pdf', '.docx', '.doc', '.txt', '.md'];

    allFiles.forEach((file) => {
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (allowedTypes.includes(fileExt)) {
        filesWithPaths.push({ file, path: file.name });
      } else {
        invalidFiles.push(file.name);
      }
    });

    if (filesWithPaths.length > 0) {
      setUploadedFiles(prev => [...prev, ...filesWithPaths]);
      toast({
        title: "Files uploaded",
        description: `${filesWithPaths.length} file(s) added successfully`,
      });
    }

    if (invalidFiles.length > 0) {
      toast({
        title: "Invalid file type",
        description: `${invalidFiles.join(', ')} - Only PDF, DOCX, DOC, TXT, and MD files are supported`,
        variant: "destructive",
      });
    }

    // Reset the input value to allow re-uploading the same files
    e.target.value = '';
  }, [toast]);

  const handleFolderInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const allFiles = Array.from(e.target.files || []);
    const filesWithPaths: FileWithPath[] = [];
    const invalidFiles: string[] = [];
    const allowedTypes = ['.pdf', '.docx', '.doc', '.txt', '.md'];

    console.log(`📁 Total files in folder selection: ${allFiles.length}`);

    // Process all files including those in nested folders
    allFiles.forEach((file) => {
      // Get file extension
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

      // Log the file path for debugging
      // @ts-ignore - webkitRelativePath exists on File in browsers
      const relativePath = file.webkitRelativePath || file.name;
      console.log(`Processing: ${relativePath}`);

      if (allowedTypes.includes(fileExt)) {
        filesWithPaths.push({ file, path: relativePath });
        console.log(`✅ Added: ${relativePath}`);
      } else {
        // Skip system files and hidden files
        if (!file.name.startsWith('.') && file.name !== 'desktop.ini' && file.name !== 'Thumbs.db') {
          invalidFiles.push(file.name);
          console.log(`❌ Skipped (invalid type): ${relativePath}`);
        } else {
          console.log(`⏭️ Skipped (system file): ${relativePath}`);
        }
      }
    });

    console.log(`✅ Valid files: ${filesWithPaths.length}, ❌ Invalid files: ${invalidFiles.length}`);

    if (filesWithPaths.length > 0) {
      setUploadedFiles(prev => [...prev, ...filesWithPaths]);
      toast({
        title: "Folder uploaded",
        description: `${filesWithPaths.length} file(s) added from folder (including subfolders)`,
      });
    } else {
      toast({
        title: "No valid files found",
        description: "The selected folder doesn't contain any PDF, DOCX, DOC, TXT, or MD files",
        variant: "destructive",
      });
    }

    if (invalidFiles.length > 0) {
      toast({
        title: "Some files skipped",
        description: `${invalidFiles.length} unsupported file(s) skipped - Only PDF, DOCX, DOC, TXT, and MD files are supported`,
        variant: "destructive",
      });
    }

    // Reset the input value to allow re-uploading the same folder
    e.target.value = '';
  }, [toast]);

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 max-w-4xl mx-auto"
    >
      <motion.div variants={itemVariants} className="text-center space-y-2">
        <h1 className="text-4xl font-bold text-primary">
          Upload Your Evidence
        </h1>
        <p className="text-secondary">Drag and drop files or folders to get started</p>
      </motion.div>

      <motion.div
        variants={itemVariants}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-12 transition-all duration-300
          bg-gradient-to-br from-amber-500/10 via-transparent to-orange-500/10
          ${isDragging
            ? 'border-amber-500 scale-[1.02]'
            : 'border-amber-400/50 hover:border-amber-400 dark:border-amber-600/50 dark:hover:border-amber-600'
          }
        `}
      >
        <div className="relative z-10 flex flex-col items-center justify-center gap-6">
          <div>
            <CloudUpload className={`w-16 h-16 transition-colors ${
              isDragging ? 'text-amber-500' : 'text-gray-400 dark:text-gray-600'
            }`} strokeWidth={1.5} />
          </div>

          <div className="text-center space-y-2">
            <p className="text-xl font-semibold text-primary">
              Drop your files here
            </p>
            <p className="text-sm text-secondary">
              Supports PDF, DOCX, TXT
            </p>
          </div>

          <div className="flex gap-3">
            <label className="cursor-pointer">
              <input
                type="file"
                multiple
                className="hidden"
                onChange={handleFileInput}
                accept=".pdf,.docx,.doc,.txt,.md"
              />
              <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 rounded-lg font-medium text-sm transition-colors border-2 border-transparent">
                <FileCheck2 className="w-4 h-4 text-white" />
                <span className="text-white">Browse Files</span>
              </div>
            </label>

            <label className="cursor-pointer">
              <input
                type="file"
                // @ts-ignore
                webkitdirectory=""
                directory=""
                multiple
                className="hidden"
                onChange={handleFolderInput}
              />
              <div className="flex items-center gap-2 px-4 py-2 border-2 border-amber-500 bg-transparent text-amber-600 dark:text-amber-400 rounded-lg font-medium text-sm transition-all hover:bg-amber-500 hover:text-white hover:border-amber-500 dark:hover:text-white">
                <FolderOpen className="w-4 h-4" />
                <span>Browse Folder</span>
              </div>
            </label>
          </div>
        </div>
      </motion.div>

      {uploadedFiles.length > 0 && (
        <motion.div
          variants={itemVariants}
          className="rounded-xl p-6 space-y-4 bg-gray-50 border border-gray-200 dark:bg-gray-800 dark:border-gray-700"
        >
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Uploaded Files ({uploadedFiles.length})
            </h3>
            <button
              onClick={() => setUploadedFiles([])}
              className="text-sm text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 font-medium transition-colors"
            >
              Clear All
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {uploadedFiles.map((fileWithPath, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg bg-white border border-gray-200 dark:bg-black dark:border-gray-700"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <FileCheck2 className="w-5 h-5 text-gray-500 dark:text-gray-500 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={fileWithPath.path}>
                      {fileWithPath.path}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500">
                      {(fileWithPath.file.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setUploadedFiles(prev => prev.filter((_, i) => i !== index))}
                  className="text-gray-400 hover:text-red-500 dark:text-gray-600 dark:hover:text-red-400 transition-colors text-lg leading-none flex-shrink-0 ml-2"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={async () => {
              try {
                // Import actions
                const { createProject } = await import("@/actions/project");
                
                // Create project with vault
                const projectResult = await createProject();
                
                if (projectResult.status !== 200 || !projectResult.data) {
                  throw new Error(projectResult.error || "Failed to create project");
                }
                
                const project = projectResult.data;
                
                // Show initial toast
                toast({
                  title: "Project Created!",
                  description: `Processing ${uploadedFiles.length} file(s)... This may take a moment.`,
                });

                // Upload files with streaming progress using SSE
                let uploadSuccessful = false;
                try {
                  console.log("📤 Starting upload with streaming progress...");
                  console.log("Files to upload:", uploadedFiles.length);

                  const formData = new FormData();
                  uploadedFiles.forEach((fileWithPath, index) => {
                    console.log(`  [${index + 1}] Adding file:`, fileWithPath.file.name);
                    formData.append('files', fileWithPath.file);
                  });
                  formData.append('project_id', project.id);

                  const folderMap: Record<string, string> = {};
                  uploadedFiles.forEach((f) => {
                    folderMap[f.file.name] = f.path;
                  });
                  formData.append('folder_paths', JSON.stringify(folderMap));

                  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005';
                  
                  // Try streaming endpoint first for real-time progress
                  try {
                    const streamResponse = await fetch(`${backendUrl}/api/upload/browser/stream`, {
                      method: 'POST',
                      body: formData,
                    });
                    
                    if (streamResponse.ok && streamResponse.body) {
                      const reader = streamResponse.body.getReader();
                      const decoder = new TextDecoder();
                      let completedCount = 0;
                      
                      while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const text = decoder.decode(value);
                        const lines = text.split('\n').filter(line => line.startsWith('data: '));
                        
                        for (const line of lines) {
                          try {
                            const data = JSON.parse(line.substring(6));
                            
                            if (data.event === 'processing') {
                              toast({
                                title: `Processing ${data.index + 1}/${data.total}`,
                                description: `📄 ${data.filename}`,
                              });
                            } else if (data.event === 'completed') {
                              completedCount++;
                              console.log(`✓ ${data.filename}: ${data.num_chunks} chunks`);
                            } else if (data.event === 'failed') {
                              console.error(`✗ ${data.filename}: ${data.error}`);
                            } else if (data.event === 'done') {
                              toast({
                                title: "Upload Complete!",
                                description: `${completedCount}/${data.total} files processed successfully.`,
                              });
                              uploadSuccessful = true;
                            }
                          } catch (e) {
                            // Ignore parse errors
                          }
                        }
                      }
                    } else {
                      throw new Error('Streaming not available');
                    }
                  } catch (streamError) {
                    // Fallback to regular upload if streaming fails
                    console.log("Streaming not available, using regular upload...");
                    
                    // Re-create FormData since it was consumed
                    const formData2 = new FormData();
                    uploadedFiles.forEach((fileWithPath) => {
                      formData2.append('files', fileWithPath.file);
                    });
                    formData2.append('project_id', project.id);
                    formData2.append('folder_paths', JSON.stringify(folderMap));
                    
                    const response = await fetch(`${backendUrl}/api/upload/browser`, {
                      method: 'POST',
                      body: formData2,
                    });

                    if (!response.ok) {
                      const errorText = await response.text();
                      throw new Error(`Upload failed: ${response.statusText}`);
                    }

                    const uploadResults = await response.json();
                    const successful = uploadResults.filter((r: any) => r.status === 'completed').length;

                    toast({
                      title: "Upload Complete!",
                      description: `${successful}/${uploadedFiles.length} files processed.`,
                    });

                    uploadSuccessful = true;
                  }
                  
                  console.log("✅ Upload complete, redirecting...");

                } catch (uploadError) {
                  console.error("❌ Upload error:", uploadError);
                  toast({
                    title: "Upload Warning",
                    description: `Project created but upload failed: ${uploadError instanceof Error ? uploadError.message : "Unknown error"}`,
                    variant: "destructive",
                  });
                }

                // Always redirect to project vault page to see uploaded files (even if upload failed, they can retry)
                const vaultUrl = `/project/${project.id}/vault`;
                console.log("🔄 REDIRECT: Navigating to:", vaultUrl);
                console.log("🔄 REDIRECT: Project ID:", project.id);
                console.log("🔄 REDIRECT: Router available:", !!router);
                console.log("🔄 REDIRECT: Upload successful:", uploadSuccessful);
                
                // Use window.location for immediate, guaranteed redirect
                window.location.href = vaultUrl;
              } catch (error) {
                console.error("Error creating project:", error);
                toast({
                  title: "Error",
                  description: error instanceof Error ? error.message : "Failed to create project",
                  variant: "destructive",
                });
              }
            }}
            className="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 rounded-lg font-semibold transition-all text-white"
          >
            <span className="text-white">Create Project with {uploadedFiles.length} file(s)</span>
          </button>
        </motion.div>
      )}
    </motion.div>
  );
}
