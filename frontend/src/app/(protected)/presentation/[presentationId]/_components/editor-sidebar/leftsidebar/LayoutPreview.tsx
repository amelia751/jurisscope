"use client";
import React from "react";
import { useSlideStore } from "@/store/useSlideStore";
import { DraggableSlidePreview } from "./DraggableSlidePreview";
import { Skeleton } from "@/components/ui/skeleton";

type Props = {
  loading?: boolean;
};

export const LayoutPreview = ({ loading }: Props) => {
  const { getOrderedSlides, reorderSlides } = useSlideStore();
  const slides = getOrderedSlides();
  const moveSlide = (dragIndex: number, hoverIndex: number) => {
    reorderSlides(dragIndex, hoverIndex);
  };

  return (
    <div className="w-64 h-full fixed left-0 top-20 border-r overflow-y-auto">
     
        <div className="p-4 pb-32 space-y-6 overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-medium dark:text-gray-100 text-gray-500">
              SLIDES
            </h2>
            <span
              className="text-xs dark:text-gray-200 text-gray-400"
              suppressHydrationWarning
            >
              {slides?.length} slides
            </span>
          </div>
          {slides.map((slide, index) => (
            <DraggableSlidePreview
              key={slide.id || index}
              slide={slide}
              index={index}
              moveSlide={moveSlide}
            />
          ))}
          {loading && <Skeleton className="h-20 w-full" />}
        </div>
 
    </div>
  );
};
