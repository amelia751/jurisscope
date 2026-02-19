import { NextRequest, NextResponse } from "next/server";
import { client } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8005";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { vault_id, column_name, question } = body;
    
    console.log("[API] Custom column request for vault:", vault_id);
    
    // Get vault to find projectId
    const vault = await client.vault.findUnique({
      where: { id: vault_id },
      select: { projectId: true },
    });
    
    const projectId = vault?.projectId || vault_id; // Fallback to vault_id as projectId
    
    // Fetch documents from BACKEND (not Prisma)
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
        { error: "No documents found in vault" },
        { status: 404 }
      );
    }
    
    // Send to backend with documents included
    const response = await fetch(`${BACKEND_URL}/api/table/custom-column`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        vault_id: projectId,
        column_name,
        question,
        documents,
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      console.error("[API] Backend error:", data);
      return NextResponse.json(
        { error: data.detail || "Failed to add custom column" },
        { status: response.status }
      );
    }
    
    console.log("[API] Custom column started:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error("[API] Custom column error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
