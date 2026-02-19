"use client";
import React, { useEffect, useState } from "react";
import EditorSidebar from "./_components/editor-sidebar/rightSidebar";
import Editor from "./_components/editor/Editor";
import { useSlideStore } from "@/store/useSlideStore";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { LayoutPreview } from "./_components/editor-sidebar/leftsidebar/LayoutPreview";
import { redirect, useParams } from "next/navigation";
import { getProjectById, updateSlides } from "@/actions/project";
import { useToast } from "@/hooks/use-toast";
import Navbar from "./_components/Navbar/Navbar";
import { useTheme } from "next-themes";
import { themes } from "@/lib/constants";
import { Loader2 } from "lucide-react";
import { generateImages } from "@/actions/chatgpt";
import { Slide } from "@/lib/types";

const Page = () => {
  const { setSlides, setProject, currentTheme, setCurrentTheme, slides, resetSlideStore } =
    useSlideStore();
  const { toast } = useToast();
  const params = useParams();
  const { setTheme } = useTheme();
  const [pageLoading, setPageLoading] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  useEffect(() => {
    (async () => {
      setIsLoading(true);
      setImageLoading(true);
      try {
        const res = await getProjectById(params.presentationId as string);
        setPageLoading(false);
        if (res.status !== 200 || !res.data) {
          setProject(null);
          resetSlideStore();
          toast({
            title: "Error",
            description: "Unable to fetch project",
            variant: "destructive",
          });
          redirect("/dashboard");
        }
        const findTheme = themes.find(
          (theme) => theme.name === res.data.themeName
        );
        console.log("🟢 Theme:", res);
        setCurrentTheme(findTheme || themes[0]);
        setTheme(findTheme?.type === "dark" ? "dark" : "light");
        setProject(res.data);

        const slides = JSON.parse(JSON.stringify(res.data.slides))
        if (res.data.slides && slides.length > 0) {
          console.log("🟢 Setting slides");
          setSlides(slides);
         
        } else {
          await fetchSlides();
        
        }
      } catch (error) {
        console.error("Error fetching slides:", error);
        toast({
          title: "Error",
          description: "An unexpected error occurred",
          variant: "destructive",
        });
        redirect("/dashboard");
      } finally {
        setIsLoading(false);
        setImageLoading(false);
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.presentationId]);


  const fetchSlides = async () => {
    try {
      const response = await fetch("/api/generateStreamLayouts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId: params.presentationId }),
      });
      if (!response.ok) {
        throw new Error("Failed to generate slides");
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const cleanedBuffer = buffer
          .replace(/```json/g, "")
          .replace(/```/g, "")
          .trim();

          console.log("🟢 Buffer:", cleanedBuffer);

        try {
          const data = JSON.parse(cleanedBuffer);
          buffer = "";
          console.log("🟢 Data:", data);
          if(data?.error) {
            toast({
              title: "Error",
              description: "An unexpected error occurred",
              variant: "destructive",
            });
            redirect("/dashboard");
          }
          setSlides(data);
          console.log("🟢 Saving");
          setIsLoading(false);



          const updateSlide = await updateSlides(
            params.presentationId as string,
            JSON.parse(JSON.stringify(slides))
          );
          if (updateSlide.status === 200 && updateSlide.data) {
            setProject(updateSlide.data);
          }

          await fetchImages(data);
        
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        } catch (error) {
          if (cleanedBuffer.startsWith("[")) {
            try {
              const repaired = cleanedBuffer.replace(/,(\s*)?$/, "") + "]";
              const data = JSON.parse(repaired);
              setSlides(data);
              console.log("🟢 repaired data:", data);
               // eslint-disable-next-line @typescript-eslint/no-unused-vars
            } catch (innerError) {
                 // Wait for more data
              // const lastValidIndex = cleanedBuffer.lastIndexOf("}");
              // if (lastValidIndex !== -1) {
              //   try {
              //     const partial =
              //       cleanedBuffer.slice(0, lastValidIndex + 1) + "]";
              //     const data = JSON.parse(partial);
              //     console.log("🟢 partial data:", data);
              //     setSlides(data);
              //   } catch {
              //     // Wait for more data
              //   }
              // }
            }
          }
        }
      }
   

  
    } catch (error) {
      console.error("Error:", error);
      toast({
        title: "Error",
        description: "An unexpected error occurred",
        variant: "destructive",
      });
      redirect("/dashboard");
    }
  };

  const fetchImages = async (slides:Slide[]) => {
   
    try {
      console.log("🟢 Fetching images...");
  
      const updatedSlides = await generateImages(slides);
      if (updatedSlides.status !== 200 || !updatedSlides.data) {
        throw new Error("Failed to generate images");
      }
  
      console.log("🟢 Images generated successfully, updating slides...", updatedSlides);
      setSlides(updatedSlides.data);
  
      // Save updated slides in the database
      const updateSlide = await updateSlides(
        params.presentationId as string,
        JSON.stringify(updatedSlides.data)
      );
  
      if (updateSlide.status === 200 && updateSlide.data) {
        setProject(updateSlide.data);
      }
    } catch (error) {
      console.error("🔴 Error generating images:", error);
      toast({
        title: "Error",
        description: "Failed to generate images",
        variant: "destructive",
      });
    } finally {
      setImageLoading(false);
    }
  };


  if(pageLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 size={48} className="animate-spin" />
      </div>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="min-h-screen flex flex-col">
        <Navbar presentationId={params.presentationId as string} />

        <div
          className="flex-1 flex overflow-hidden pt-16"
          style={{
            color: currentTheme.accentColor,
            fontFamily: currentTheme.fontFamily,
            backgroundColor: currentTheme.backgroundColor,
          }}
        >
          <LayoutPreview loading={isLoading} />

          <div className="flex-1 ml-64 pr-16">
            <Editor
              isEditable={true}
              loading={isLoading}
              imageLoading={imageLoading}
            />
          </div>
          <EditorSidebar />
        </div>
      </div>
    </DndProvider>
  );
};

export default Page;