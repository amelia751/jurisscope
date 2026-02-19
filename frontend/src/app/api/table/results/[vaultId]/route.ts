import { NextRequest, NextResponse } from "next/server";
import { client } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8005";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ vaultId: string }> }
) {
  try {
    const { vaultId } = await params;
    
    console.log("[API] Getting documents for vault:", vaultId);
    
    // Get vault to find projectId
    const vault = await client.vault.findUnique({
      where: { id: vaultId },
      select: { projectId: true },
    });
    
    const projectId = vault?.projectId || vaultId; // Fallback to vaultId as projectId
    
    // Fetch documents from BACKEND API (where they're actually stored)
    let documents: any[] = [];
    try {
      const response = await fetch(`${BACKEND_URL}/api/documents?project_id=${projectId}`, {
        cache: 'no-store',
      });
      if (response.ok) {
        const data = await response.json();
        documents = (data.documents || []).map((doc: any) => ({
          id: doc.id,
          name: doc.title,
          originalName: doc.title,
          mimeType: doc.mime || 'application/pdf',
          status: doc.status === 'indexed' ? 'completed' : doc.status,
          firestoreDocId: doc.id,
          analysis: null, // Will be fetched separately if needed
        }));
      }
    } catch (error) {
      console.error("[API] Failed to fetch documents from backend:", error);
    }
    
    console.log("[API] Found", documents.length, "documents from backend");
    
    if (documents.length === 0) {
      return NextResponse.json([]);
    }
    
    // Fetch analysis results from backend (if available)
    let analysisResults: any[] = [];
    try {
      const response = await fetch(`${BACKEND_URL}/api/table/results/${vaultId}`);
      if (response.ok) {
        analysisResults = await response.json();
        console.log("[API] Retrieved", analysisResults.length, "analysis results");
      }
    } catch (error) {
      // Analysis may not exist yet
    }
    
    // Merge analysis if available
    if (analysisResults.length > 0) {
      const analysisMap = new Map();
      for (const result of analysisResults) {
        if (result.id) {
          analysisMap.set(result.id, result.analysis);
        }
      }
      documents = documents.map(doc => ({
        ...doc,
        analysis: analysisMap.get(doc.id) || analysisMap.get(doc.firestoreDocId) || null,
      }));
    }
    
    console.log("[API] Returning", documents.length, "documents");
    return NextResponse.json(documents);
    
  } catch (error) {
    console.error("[API] Get results error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ vaultId: string }> }
) {
  try {
    const { vaultId } = await params;
    
    const response = await fetch(`${BACKEND_URL}/api/table/results/${vaultId}`, {
      method: "DELETE",
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Failed to delete results" },
        { status: response.status }
      );
    }
    
    return NextResponse.json(data);
    
  } catch (error) {
    console.error("[API] Delete results error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

