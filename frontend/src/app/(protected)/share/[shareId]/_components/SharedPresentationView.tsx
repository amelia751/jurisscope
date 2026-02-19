"use client";
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MasterRecursiveComponent } from "@/app/(protected)/presentation/[presentationId]/_components/editor/MasterRecursiveComponent";
import { Project } from "@prisma/client";
import { themes } from "@/lib/constants";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function SharedPresentationView({ project }: { project: Project }) {
  console.log(project);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const slides = JSON.parse(JSON.stringify(project.slides));

  const theme = themes.find((theme) => theme.name === project.themeName) || themes[0];

  
  const goToNextSlide = useCallback(() => {
    setCurrentSlideIndex((prevIndex) => (prevIndex + 1) % slides.length);
  }, [slides.length]);

  const goToPreviousSlide = useCallback(() => {
    setCurrentSlideIndex(
      (prevIndex) => (prevIndex - 1 + slides.length) % slides.length
    );
  }, [slides.length]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        goToNextSlide();
      } else if (e.key === "ArrowLeft") {
        goToPreviousSlide();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [goToNextSlide, goToPreviousSlide]);

  if (slides.length === 0) {
    return (
      <div className="w-full h-full flex justify-center items-center">
        No slides available.
      </div>
    );
  }

  return (
    <div
      className="w-screen h-screen overflow-hidden relative"

    >
      <AnimatePresence mode="wait">
        <motion.div
          key={currentSlideIndex}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 1.2 }}
          transition={{ duration: 0.5 }}
          className={`w-full h-full pointer-events-none ${slides[currentSlideIndex].className}`}
          style={{
            color: theme.accentColor,
            fontFamily: theme.fontFamily,
            backgroundColor: theme.slideBackgroundColor,
            backgroundImage: theme.gradientBackground,
          }}
        >
        
            <MasterRecursiveComponent
              content={slides[currentSlideIndex].content}
              onContentChange={() => {}}
              slideId={slides[currentSlideIndex].id}
              isPreview={false}
              isEditable={false}
              imageLoading={false}
            />

        </motion.div>
      </AnimatePresence>
      <button
        onClick={goToPreviousSlide}
        className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full"
        aria-label="Previous slide"
      >
        <ChevronLeft size={24} />
      </button>
      <button
        onClick={goToNextSlide}
        className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full"
        aria-label="Next slide"
      >
        <ChevronRight size={24} />
      </button>
    </div>
  );
}
