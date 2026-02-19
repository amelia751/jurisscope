import { getProjectById } from '@/actions/project';
import { getVaultByProjectId } from '@/actions/vault';
import { redirect } from 'next/navigation';
import { TableReview } from './_components/TableReview';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function TablePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  // Fetch project
  const projectResult = await getProjectById(projectId);

  if (projectResult.status !== 200 || !projectResult.data) {
    redirect('/dashboard');
  }

  const project = projectResult.data;
  
  // Get vault (for vaultId) - create if doesn't exist
  const vaultResult = await getVaultByProjectId(projectId);
  // Use projectId as vaultId fallback since documents are keyed by projectId in backend
  const vaultId = vaultResult.status === 200 && vaultResult.data ? vaultResult.data.id : projectId;

  return <TableReview projectTitle={project.title} projectId={projectId} vaultId={vaultId} />;
}
