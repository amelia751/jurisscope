import { getProjectById } from '@/actions/project';
import { getVaultByProjectId } from '@/actions/vault';
import { redirect } from 'next/navigation';
import ChatInterface from './_components/ChatInterface';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

// Use BACKEND_URL for server-side fetch, fallback to localhost for local dev
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005';

export default async function DiscoverPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  // Fetch project from Prisma
  const projectResult = await getProjectById(projectId);

  if (projectResult.status !== 200 || !projectResult.data) {
    redirect('/dashboard');
  }

  const project = projectResult.data;
  
  // Fetch vault structure from Prisma
  const vaultResult = await getVaultByProjectId(projectId);
  const vaultData = vaultResult.status === 200 && vaultResult.data ? vaultResult.data : null;
  
  // Fetch documents from BACKEND API
  let backendDocuments: any[] = [];
  try {
    console.log(`[DiscoverPage] Fetching documents from: ${BACKEND_URL}/api/documents?project_id=${projectId}`);
    const response = await fetch(`${BACKEND_URL}/api/documents?project_id=${projectId}`, {
      cache: 'no-store',
    });
    console.log(`[DiscoverPage] Response status: ${response.status}`);
    if (response.ok) {
      const data = await response.json();
      console.log(`[DiscoverPage] Fetched ${data.documents?.length || 0} documents`);
      backendDocuments = (data.documents || []).map((doc: any) => ({
        id: doc.id,
        name: doc.title,
        originalName: doc.title,
        folderId: null,
        status: doc.status === 'indexed' ? 'completed' : doc.status,
        uploadedAt: doc.created_at,
        size: '0',
        mimeType: doc.mime || 'application/pdf',
        path: doc.file_path || '',
      }));
    }
  } catch (error) {
    console.error('[DiscoverPage] Failed to fetch documents from backend:', error);
  }

  // Build vault with backend documents
  const vault = vaultData ? {
    ...vaultData,
    Documents: backendDocuments,
    Folders: vaultData.Folders || [],
  } : {
    id: projectId,
    name: 'Evidence',
    Documents: backendDocuments,
    Folders: [],
  };

  return <ChatInterface project={project} vault={vault} />;
}

