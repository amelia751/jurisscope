import { NextRequest, NextResponse } from "next/server";
import { client } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8005";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { vault_id, template } = body;
    
    console.log("[API] Batch analyze request for vault:", vault_id);
    
    // Get vault to find projectId
    const vault = await client.vault.findUnique({
      where: { id: vault_id },
      select: { projectId: true },
    });
    
    const projectId = vault?.projectId || vault_id; // Fallback to vault_id as projectId
    
    // Fetch documents from BACKEND (not Prisma - documents are stored in backend)
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
          mimeType: doc.mime || 'application/pdf',
          status: doc.status === 'indexed' ? 'completed' : doc.status,
          firestoreDocId: doc.id,
        }));
      }
    } catch (error) {
      console.error("[API] Failed to fetch documents from backend:", error);
    }
    
    console.log("[API] Found", documents.length, "documents from backend");
    
    if (documents.length === 0) {
      return NextResponse.json(
        { error: "No documents found in vault. Please upload documents first." },
        { status: 404 }
      );
    }
    
    // Send to backend with documents included
    const response = await fetch(`${BACKEND_URL}/api/table/batch-analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        vault_id: projectId, // Use projectId for backend
        template,
        documents,
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      console.error("[API] Backend error:", data);
      return NextResponse.json(
        { error: data.detail || "Failed to start batch analysis" },
        { status: response.status }
      );
    }
    
    console.log("[API] Batch analyze started:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error("[API] Batch analyze error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
