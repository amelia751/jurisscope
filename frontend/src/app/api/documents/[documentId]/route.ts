import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ documentId: string }> }
) {
  try {
    const { documentId } = await params;
    
    console.log('[Documents API] Fetching document:', documentId);
    
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005';
    
    try {
      // Step 1: Get signed URL from backend
      console.log('[Documents API] Getting signed URL for:', documentId);
      const signedUrlResponse = await fetch(`${backendUrl}/api/signed-url/${documentId}`);
      
      if (signedUrlResponse.ok) {
        const { signed_url } = await signedUrlResponse.json();
        console.log('[Documents API] Got signed URL, redirecting...');
        
        // Step 2: Fetch the actual document from GCS using signed URL
        const docResponse = await fetch(signed_url);
        
        if (docResponse.ok) {
          console.log('[Documents API] Successfully fetched document from GCS');
          const document = await docResponse.blob();
          
          return new NextResponse(document, {
            headers: {
              'Content-Type': docResponse.headers.get('Content-Type') || 'application/pdf',
              'Cache-Control': 'public, max-age=3600',
            },
          });
        } else {
          console.warn('[Documents API] GCS fetch failed:', docResponse.status);
        }
      } else {
        console.warn('[Documents API] Signed URL request failed:', signedUrlResponse.status);
      }
    } catch (fetchError) {
      console.error('[Documents API] Fetch failed:', fetchError);
    }
    
    // Fallback: Document not available
    console.log('[Documents API] Document not available, showing helpful message');
    
    return NextResponse.json({
      error: 'Document Preview Unavailable',
      message: 'The document could not be loaded from storage.',
      documentId: documentId,
      suggestion: 'The cited text is shown in the yellow banner above.',
      helpText: 'This may happen if the document has not been uploaded to Google Cloud Storage yet, or if the document ID is incorrect.',
    }, { 
      status: 404,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error('[Documents API] Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to fetch document',
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}

