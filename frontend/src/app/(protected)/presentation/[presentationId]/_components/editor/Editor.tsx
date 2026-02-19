"use client";

import React, { useRef, useEffect, useCallback } from "react";
import { useSlideStore } from "@/store/useSlideStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { MasterRecursiveComponent } from "./MasterRecursiveComponent";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { EllipsisVertical, Trash } from "lucide-react";
import { useDrag, useDrop } from "react-dnd";
import { v4 as uuidv4 } from "uuid";
import { LayoutSlides, Slide } from "@/lib/types";
import { updateSlides } from "@/actions/project";
import { Skeleton } from "@/components/ui/skeleton";

interface DraggableSlideProps {
  slide: Slide;
  index: number;
  moveSlide: (dragIndex: number, hoverIndex: number) => void;
  handleDelete: (id: string) => void;
  isEditable: boolean;
  imageLoading: boolean;
}

const DraggableSlide: React.FC<DraggableSlideProps> = ({
  slide,
  index,
  moveSlide,
  handleDelete,
  isEditable,
  imageLoading=false
}) => {
  const ref = useRef(null);
  const { currentSlide, setCurrentSlide, currentTheme, updateContentItem } =
    useSlideStore();

  const [{ isDragging }, drag] = useDrag({
    type: "SLIDE",
    item: { index, type: "SLIDE" },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: isEditable,
  });

  const [, drop] = useDrop({
    accept: ["SLIDE", "LAYOUT"],
    hover(item: { index: number; type: string }) {
      if (!ref.current || !isEditable) {
        return;
      }
      const dragIndex = item.index;
      const hoverIndex = index;

      if (item.type === "SLIDE") {
        if (dragIndex === hoverIndex) {
          return;
        }
        moveSlide(dragIndex, hoverIndex);
        item.index = hoverIndex;
      }
    },
  });

  drag(drop(ref));

  const handleContentChange = (
    contentId: string,
    newContent: string | string[] | string[][]
  ) => {
    console.log("Content changed", slide, contentId, newContent);
    if (isEditable) {
      updateContentItem(slide.id, contentId, newContent);
    }
  };

  return (
    <div
      ref={ref}
      className={cn(
        "w-full rounded-lg shadow-lg relative p-0 min-h-[400px] max-h-[800px]",
        "shadow-xl transition-shadow duration-300",
        "flex flex-col",
        index === currentSlide ? "ring-2 ring-blue-500 ring-offset-2" : "",
        slide.className,
        isDragging ? "opacity-50" : "opacity-100"
      )}
      onClick={() => setCurrentSlide(index)}
      style={{
        backgroundImage: currentTheme.gradientBackground,
      }}
    >
      <div className="w-full h-full flex-grow overflow-hidden">
        <MasterRecursiveComponent
          content={slide.content}
          onContentChange={handleContentChange}
          slideId={slide.id}
          isPreview={false}
          isEditable={isEditable}
          imageLoading={imageLoading}
        />
      </div>

      {isEditable && (
        <Popover>
          <PopoverTrigger asChild className="absolute top-2 left-2">
            <Button size="sm" variant="outline">
              <EllipsisVertical className="w-5 h-5" />
              <span className="sr-only">Slide options</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-fit p-0">
            <div className="flex space-x-2">
              <Button variant="ghost" onClick={() => handleDelete(slide.id)}>
                <Trash className="w-5 h-5 text-red-500" />
                <span className="sr-only">Delete slide</span>
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
};

interface DropZoneProps {
  index: number;
  onDrop: (
    item: {
      type: string;
      layoutType: string;
      component: LayoutSlides;
      index?: number;
    },
    dropIndex: number
  ) => void;
  isEditable: boolean;
}

const DropZone: React.FC<DropZoneProps> = ({ index, onDrop, isEditable }) => {
  const [{ isOver, canDrop }, dropRef] = useDrop({
    accept: ["SLIDE", "layout"],
    drop: (item: {
      type: string;
      layoutType: string;
      component: LayoutSlides;
      index?: number;
    }) => {
      onDrop(item, index);
    },
    canDrop: () => isEditable,
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
      canDrop: !!monitor.canDrop(),
    }),
  });

  if (!isEditable) return null;

  return (
    <div
      ref={dropRef as unknown as React.RefObject<HTMLDivElement>}
      className={cn(
        "h-4 my-2 rounded-md transition-all duration-200",
        isOver && canDrop ? "border-green-500 bg-green-100" : "border-gray-300",
        canDrop ? "border-blue-300" : ""
      )}
    >
      {isOver && canDrop && (
        <div className="h-full flex items-center justify-center text-green-600">
          Drop here
        </div>
      )}
    </div>
  );
};

interface EditorProps {
  isEditable: boolean;
  loading?: boolean;
  imageLoading: boolean;
}

const Editor: React.FC<EditorProps> = ({
  isEditable,
  loading,
  imageLoading=false
}: EditorProps) => {
  const {
    getOrderedSlides,
    currentSlide,
    removeSlide,
    addSlideAtIndex,
    reorderSlides,
    slides,
    project,
  } = useSlideStore();

  const orderedSlides = getOrderedSlides();
  const slideRefs = useRef<(HTMLDivElement | null)[]>([]);

  const handleDelete = (id: string) => {
    if (isEditable) {
      console.log("Deleting", id);
      removeSlide(id);
    }
  };

  const moveSlide = (dragIndex: number, hoverIndex: number) => {
    if (isEditable) {
      reorderSlides(dragIndex, hoverIndex);
    }
  };

  const handleDrop = (
    item: {
      type: string;
      layoutType: string;
      component: LayoutSlides;
      index?: number;
    },
    dropIndex: number
  ) => {
    if (!isEditable) return;

    if (item.type === "layout") {
      addSlideAtIndex(
        { ...item.component, id: uuidv4(), slideOrder: dropIndex },
        dropIndex
      );
    } else if (item.type === "SLIDE" && item.index !== undefined) {
      moveSlide(item.index, dropIndex);
    }
  };

  useEffect(() => {
    if (slideRefs.current[currentSlide]) {
      slideRefs.current[currentSlide]?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentSlide]);

  // Autosave feature
  const autosaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const saveSlides = useCallback(() => {
    if (isEditable && project) {
      console.log("Autosaving slides...");
      // Implement your save logic here, e.g., API call or local storage
      (async () => {
        await updateSlides(project.id, JSON.parse(JSON.stringify(slides)));
        // console.log("🟢 Slides saved successfully", res);
      })();
    }
  }, [isEditable, project, slides]);

  useEffect(() => {
    if (autosaveTimeoutRef.current) {
      clearTimeout(autosaveTimeoutRef.current);
    }

    if (isEditable) {
      autosaveTimeoutRef.current = setTimeout(() => {
        saveSlides();
      }, 2000); // 2 seconds debounce
    }

    return () => {
      if (autosaveTimeoutRef.current) {
        clearTimeout(autosaveTimeoutRef.current);
      }
    };
  }, [slides, saveSlides, isEditable]);

  return (
    <div className="flex-1 flex flex-col h-full max-w-3xl mx-auto px-4 mb-20">
      <ScrollArea className="flex-1 mt-8">
        <div className="px-4 pb-4 space-y-4 pt-2">
          {isEditable && (
            <DropZone index={0} onDrop={handleDrop} isEditable={isEditable} />
          )}
          {orderedSlides.map((slide, index) => (
            <React.Fragment key={slide.id || index}>
              <DraggableSlide
                slide={slide}
                index={index}
                moveSlide={moveSlide}
                handleDelete={handleDelete}
                isEditable={isEditable}
                imageLoading={imageLoading}
              />
              {isEditable && (
                <DropZone
                  index={index + 1}
                  onDrop={handleDrop}
                  isEditable={isEditable}
                />
              )}
            </React.Fragment>
          ))}

          {loading && (
            <div className="w-full px-4 flex flex-col space-y-6">
              <Skeleton className="h-52 w-full" />
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

export default Editor;
