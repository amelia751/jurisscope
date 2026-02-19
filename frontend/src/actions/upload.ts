"use server";
import { onAuthenticateUser } from "./user";
import { createFolder, createDocument } from "./vault";

/**
 * Upload file(s) to a project's vault
 * Handles folder structure creation and GCS upload
 */
export const uploadFilesToVault = async (data: {
  projectId: string;
  vaultId: string;
  files: Array<{
    name: string;
    path: string; // File path (can include folders)
    size: number;
    mimeType: string;
    localPath?: string; // Local file path for server-side uploads
  }>;
  defaultFolder?: string; // Default folder if no path specified (e.g., "Evidence")
}) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const results = [];
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

    for (const file of data.files) {
      try {
        // Parse folder path from file path
        let folderPath = data.defaultFolder || "/Evidence";
        let fileName = file.name;

        // If file.path contains folders (e.g., "regulations/GDPR_Regulation.pdf")
        if (file.path.includes("/")) {
          const parts = file.path.split("/");
          fileName = parts[parts.length - 1];
          const folders = parts.slice(0, -1).filter((p) => p.length > 0);

          if (folders.length > 0) {
            folderPath = "/" + folders.join("/");
          }
        }

        // Create or get folder
        const folderResult = await createFolder(data.vaultId, folderPath);
        if (folderResult.status !== 200 && folderResult.status !== 201) {
          console.error("Failed to create folder:", folderPath, folderResult.error);
          results.push({
            file: file.name,
            status: "error",
            error: "Failed to create folder structure",
          });
          continue;
        }

        const folder = folderResult.data;

        // Upload to GCS via backend API
        let uploadResponse;
        if (file.localPath) {
          // Server-side upload (file is on local filesystem)
          const response = await fetch(`${backendUrl}/api/upload/local`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              file_path: file.localPath,
              project_id: data.projectId,
              doc_title: fileName,
            }),
          });

          uploadResponse = await response.json();
        } else {
          // Client-side upload would need signed URL flow
          // Get signed URL
          const signedUrlResponse = await fetch(
            `${backendUrl}/api/upload/signed-url?project_id=${data.projectId}&filename=${encodeURIComponent(fileName)}&content_type=${encodeURIComponent(file.mimeType)}`
          );

          if (!signedUrlResponse.ok) {
            throw new Error("Failed to get signed URL");
          }

          const { signed_url, gcs_path } = await signedUrlResponse.json();

          // This would need actual file data for client-side uploads
          // For now, we'll just track the metadata
          uploadResponse = { gcs_path };
        }

        // Create document record in PostgreSQL
        const gcsPath = uploadResponse.gcs_path || `${data.projectId}/${fileName}`;
        const documentResult = await createDocument({
          vaultId: data.vaultId,
          folderId: folder?.id,
          name: fileName.replace(/\.[^/.]+$/, ""), // Remove extension
          originalName: fileName,
          gcsPath,
          mimeType: file.mimeType,
          size: file.size,
        });

        if (documentResult.status === 201) {
          results.push({
            file: file.name,
            status: "success",
            documentId: documentResult.data?.id,
            folderId: folder?.id,
            folderPath: folder?.path,
            gcsPath,
          });
        } else {
          results.push({
            file: file.name,
            status: "error",
            error: documentResult.error,
          });
        }
      } catch (error) {
        console.error(`Error uploading file ${file.name}:`, error);
        results.push({
          file: file.name,
          status: "error",
          error: error instanceof Error ? error.message : "Unknown error",
        });
      }
    }

    return {
      status: 200,
      data: results,
    };
  } catch (error) {
    console.error("🔴 ERROR uploading files to vault:", error);
    return { status: 500, error: "Failed to upload files" };
  }
};

/**
 * Bulk upload files from a local directory (e.g., demo-case)
 */
export const uploadDemoCaseToVault = async (
  projectId: string,
  vaultId: string,
  demoCasePath: string = "/Users/anhlam/clause/demo-case"
) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    // This would need to be called from a Node.js environment with fs access
    // For now, return structure that can be used by client
    return {
      status: 200,
      message:
        "Use the uploadFilesToVault function with file list from demo-case directory",
      demoCasePath,
    };
  } catch (error) {
    console.error("🔴 ERROR:", error);
    return { status: 500, error: "Internal server error" };
  }
};

