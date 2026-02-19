'use client';
import { Project } from "@prisma/client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Trash } from "@/icons/Trash";
import { AlertDialogBox } from "@/components/global/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { deleteAllProjects } from "@/actions/project";
import { useRouter } from "next/navigation";

type Props = {
  Projects: Project[];
};

const DeleteAllButton = ({ Projects }: Props) => {
  const { toast } = useToast();
  const router = useRouter();
  const[loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);


  const handleDeleteAllProjects = async () => {
    setLoading(true);
    if(Projects.length === 0) {
      setLoading(false);
      toast({
        title: "Error",
        description: "No projects found",
        variant: "destructive",
      });
      return;
    }

    try {
      // delete all projects
      const res = await deleteAllProjects(Projects.map((project) => project.id));
      if(res.status !== 200) {
        throw new Error("Failed to delete all projects");
      }
      router.refresh();
      setOpen(false);
      toast({
        title: "Success",
        description: "All projects deleted successfully",
      });
    } catch (e) {
      console.error(e);
      toast({
        title: "Error",
        description: "Failed to delete all projects",
        variant: "destructive",
      });
    }
    finally {
      
      setLoading(false);
    }
  };
  return (
    <AlertDialogBox
      description=" This action cannot be undone. This will permanently delete all your
      projects and remove your data from our servers."
      className="bg-red-500 text-white dark:bg-red-600 hover:bg-red-600 dark:hover:bg-red-700"
      onClick={handleDeleteAllProjects}
      loading={loading}
      handleOpen={()=>setOpen(!open)}
      open={open}
    >
      <Button
        size={"lg"}
        className="bg-background-80 rounded-lg dark:hover:bg-background-90 text-primary
    font-semibold hover:text-white"
      >
        <Trash />
        Delete All
      </Button>
    </AlertDialogBox>
  );
};

export default DeleteAllButton;
