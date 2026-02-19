import { containerVariants, itemVariants, timeAgo } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";
import usePromptStore from "@/store/usePromptStore";
import useCreativeAIStore from "@/store/useCreativeAiStore";
import { useToast } from "@/hooks/use-toast";

export const RecentPrompts = () => {
  const {prompts, setPage} = usePromptStore();
  const {addMultipleOutlines, setCurrentAiPrompt} = useCreativeAIStore();
  const {toast} = useToast();

  const handleEdit = (id:string) => {
    const prompt = prompts.find((prompt) => prompt?.id === id);
    
    if(prompt){
      setPage("creative-ai");
      addMultipleOutlines(
        prompt?.outlines
      )
      setCurrentAiPrompt(prompt?.title);
    }
    else{
      toast({
        title: "Error",
        description: "Prompt not found",
        variant:"destructive",
        duration:2000
      });
    }
   
  }
  return (
    <motion.div variants={containerVariants} className="space-y-4 !mt-20">
      <motion.h2
        variants={itemVariants}
        className="text-2xl font-semibold text-center"
      >
        Your Recent Prompts
      </motion.h2>
      <motion.div
        variants={containerVariants}
        className="space-y-2 w-full lg:max-w-[80%] mx-auto"
      >
        {prompts?.map((prompt, i) => (
          <motion.div key={i} variants={itemVariants}>
            <Card className="p-4 flex items-center justify-between hover:bg-accent/50 transition-colors duration-300">
              <div className="max-w-[70%]">
                <h3 className="font-semibold text-xl line-clamp-1">{prompt?.title}</h3>
                <p className="font-semibold text-sm text-muted-foreground">
                  {timeAgo(prompt?.createdAt)}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm text-clause">Creative AI</span>

                <Button
                  variant="default"
                  size="sm"
                  className="rounded-xl bg-primary-20 dark:hover:bg-gray-700 hover:bg-gray-200 text-primary"
                  onClick={()=>handleEdit(prompt?.id)}
                >
                  Edit
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
};
