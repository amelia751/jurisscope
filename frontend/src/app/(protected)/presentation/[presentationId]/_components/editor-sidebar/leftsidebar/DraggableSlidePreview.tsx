import { cn } from "@/lib/utils";
import { useDrag, useDrop } from "react-dnd";
import { Slide } from "@/lib/types";
import { useRef } from "react";
import { useSlideStore } from "@/store/useSlideStore";
import { ScaledPreview } from "./SlidePreview";

export const DraggableSlidePreview: React.FC<{
  slide: Slide;
  index: number;
  moveSlide: (dragIndex: number, hoverIndex: number) => void;
}> = ({ slide, index, moveSlide }) => {
  const { currentSlide, setCurrentSlide } = useSlideStore();
  const ref = useRef<HTMLDivElement>(null);

  const [{ isDragging }, drag] = useDrag({
    type: "SLIDE",
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [, drop] = useDrop({
    accept: "SLIDE",
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    hover(item: { index: number }, monitor) {
      if (!ref.current) {
        return;
      }
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) {
        return;
      }
      moveSlide(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      className={cn(
        "relative cursor-pointer group",
        index === currentSlide ? "before:bg-blue-500" : "before:bg-transparent",
        isDragging ? "opacity-50" : "opacity-100"
      )}
      onClick={() => setCurrentSlide(index)}
    >
      <div className="pl-2 mb-4 relative">
        <ScaledPreview
          slide={slide}
          isActive={index === currentSlide}
          index={index}
        />
      </div>
    </div>
  );
};
