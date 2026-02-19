"use server";
import { client } from "@/lib/prisma";
import { onAuthenticateUser } from "./user";

/**
 * Create a vault for a project (automatically created with project)
 */
export const createVault = async (projectId: string, name: string = "Evidence") => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    // Create the vault
    const vault = await client.vault.create({
      data: {
        projectId,
        name,
      },
    });

    return { status: 201, data: vault };
  } catch (error) {
    console.error("🔴 ERROR creating vault:", error);
    return { status: 500, error: "Failed to create vault" };
  }
};

/**
 * Get vault by project ID
 */
export const getVaultByProjectId = async (projectId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const vault = await client.vault.findUnique({
      where: { projectId },
      include: {
        Folders: {
          orderBy: { path: "asc" },
        },
        Documents: {
          orderBy: { uploadedAt: "desc" },
        },
      },
    });

    if (!vault) {
      return { status: 404, error: "Vault not found" };
    }

    return { status: 200, data: vault };
  } catch (error) {
    console.error("🔴 ERROR fetching vault:", error);
    return { status: 500, error: "Failed to fetch vault" };
  }
};

/**
 * Create or get folder with nested path support
 * Example: createFolder(vaultId, "/regulations/EU/GDPR")
 */
export const createFolder = async (vaultId: string, folderPath: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    // Normalize path (remove trailing slash, ensure leading slash)
    const normalizedPath = folderPath.startsWith("/") ? folderPath : `/${folderPath}`;
    const cleanPath = normalizedPath.replace(/\/+$/, "");

    // Check if folder already exists
    const existingFolder = await client.folder.findUnique({
      where: {
        vaultId_path: {
          vaultId,
          path: cleanPath,
        },
      },
    });

    if (existingFolder) {
      return { status: 200, data: existingFolder };
    }

    // Split path into parts and create nested structure
    const pathParts = cleanPath.split("/").filter((p) => p.length > 0);
    let currentPath = "";
    let parentFolderId: string | null = null;

    for (let i = 0; i < pathParts.length; i++) {
      currentPath += `/${pathParts[i]}`;

      // Check if this level exists
      let folder = await client.folder.findUnique({
        where: {
          vaultId_path: {
            vaultId,
            path: currentPath,
          },
        },
      });

      // Create if doesn't exist
      if (!folder) {
        folder = await client.folder.create({
          data: {
            vaultId,
            name: pathParts[i],
            path: currentPath,
            parentFolderId,
            depth: i,
          },
        });
      }

      parentFolderId = folder.id;
    }

    // Return the final folder
    const finalFolder = await client.folder.findUnique({
      where: {
        vaultId_path: {
          vaultId,
          path: cleanPath,
        },
      },
    });

    return { status: 201, data: finalFolder };
  } catch (error) {
    console.error("🔴 ERROR creating folder:", error);
    return { status: 500, error: "Failed to create folder" };
  }
};

/**
 * Get folder tree for a vault
 */
export const getFolderTree = async (vaultId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const folders = await client.folder.findMany({
      where: { vaultId },
      include: {
        Documents: true,
        ChildFolders: true,
      },
      orderBy: { path: "asc" },
    });

    return { status: 200, data: folders };
  } catch (error) {
    console.error("🔴 ERROR fetching folder tree:", error);
    return { status: 500, error: "Failed to fetch folder tree" };
  }
};

/**
 * Create document record (after uploading to GCS)
 */
export const createDocument = async (data: {
  vaultId: string;
  folderId?: string;
  name: string;
  originalName: string;
  gcsPath: string;
  mimeType: string;
  size: number;
}) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const document = await client.document.create({
      data: {
        vaultId: data.vaultId,
        folderId: data.folderId || null,
        name: data.name,
        originalName: data.originalName,
        gcsPath: data.gcsPath,
        mimeType: data.mimeType,
        size: BigInt(data.size),
      },
    });

    return { status: 201, data: document };
  } catch (error) {
    console.error("🔴 ERROR creating document:", error);
    return { status: 500, error: "Failed to create document" };
  }
};

/**
 * Update document status after processing
 */
export const updateDocumentStatus = async (
  documentId: string,
  status: string,
  firestoreDocId?: string,
  elasticsearchIds?: string[]
) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const document = await client.document.update({
      where: { id: documentId },
      data: {
        status,
        processedAt: status === "completed" ? new Date() : null,
        firestoreDocId: firestoreDocId || undefined,
        elasticsearchIds: elasticsearchIds || undefined,
      },
    });

    return { status: 200, data: document };
  } catch (error) {
    console.error("🔴 ERROR updating document status:", error);
    return { status: 500, error: "Failed to update document status" };
  }
};

/**
 * Get documents by folder
 */
export const getDocumentsByFolder = async (folderId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const documents = await client.document.findMany({
      where: { folderId },
      orderBy: { uploadedAt: "desc" },
    });

    return { status: 200, data: documents };
  } catch (error) {
    console.error("🔴 ERROR fetching documents:", error);
    return { status: 500, error: "Failed to fetch documents" };
  }
};

/**
 * Get all documents in a vault
 */
export const getDocumentsByVault = async (vaultId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const documents = await client.document.findMany({
      where: { vaultId },
      include: {
        Folder: true,
      },
      orderBy: { uploadedAt: "desc" },
    });

    return { status: 200, data: documents };
  } catch (error) {
    console.error("🔴 ERROR fetching vault documents:", error);
    return { status: 500, error: "Failed to fetch vault documents" };
  }
};

/**
 * Rename a folder
 */
export const renameFolder = async (folderId: string, newName: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const folder = await client.folder.update({
      where: { id: folderId },
      data: { name: newName },
    });

    return { status: 200, data: folder };
  } catch (error) {
    console.error("🔴 ERROR renaming folder:", error);
    return { status: 500, error: "Failed to rename folder" };
  }
};

/**
 * Delete a folder and its documents
 */
export const deleteFolder = async (folderId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    await client.folder.delete({
      where: { id: folderId },
    });

    return { status: 200, message: "Folder deleted successfully" };
  } catch (error) {
    console.error("🔴 ERROR deleting folder:", error);
    return { status: 500, error: "Failed to delete folder" };
  }
};

/**
 * Rename a document
 */
export const renameDocument = async (documentId: string, newName: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    const document = await client.document.update({
      where: { id: documentId },
      data: { name: newName },
    });

    return { status: 200, data: document };
  } catch (error) {
    console.error("🔴 ERROR renaming document:", error);
    return { status: 500, error: "Failed to rename document" };
  }
};

/**
 * Delete a document
 */
export const deleteDocument = async (documentId: string) => {
  try {
    const checkUser = await onAuthenticateUser();

    if (checkUser.status !== 200 || !checkUser.user) {
      return { status: 403, error: "User not authenticated" };
    }

    await client.document.delete({
      where: { id: documentId },
    });

    return { status: 200, message: "Document deleted successfully" };
  } catch (error) {
    console.error("🔴 ERROR deleting document:", error);
    return { status: 500, error: "Failed to delete document" };
  }
};

