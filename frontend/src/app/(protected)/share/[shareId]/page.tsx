import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { SharedPresentationView } from "./_components/SharedPresentationView";
import { getProjectById } from "@/actions/project";
import { redirect } from "next/navigation";


type props = {
  params: Promise<{
    shareId: string;
  }>;
};

function LoadingView() {
  return (
    <div className="flex items-center justify-center h-screen">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
      <span className="sr-only">Loading presentation...</span>
    </div>
  );
}

const SharePage = async({ params }: props) => {
  const shareId = (await params).shareId;
  const project = await getProjectById(shareId);
  if(!project.data) {
    redirect('/dashboard');
  }
  return (
    <Suspense fallback={<LoadingView />}>
      <SharedPresentationView project={project.data} />
    </Suspense>
  );
};

export default SharePage;
