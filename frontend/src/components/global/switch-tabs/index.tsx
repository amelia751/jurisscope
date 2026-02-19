import { TabsList, TabsTrigger } from "@/components/ui/tabs";

export const SwitchTabs = () => {
  return (
    <TabsList className="bg-primary-90">
      <TabsTrigger value="all" className="hover:bg-background">All</TabsTrigger>
      <TabsTrigger value="recent" className="hover:bg-background">Recent</TabsTrigger>
      <TabsTrigger value="shared" className="hover:bg-background">Shared</TabsTrigger>
    </TabsList>
  );
};
