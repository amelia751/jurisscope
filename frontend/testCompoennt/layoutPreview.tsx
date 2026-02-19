// import React from "react";
// import { useSlideStore } from "@/store/useSlideStore";
// import { ContentItem, Slide } from "@/store/useSlideStore";
// import { ScrollArea } from "@/components/ui/scroll-area";
// import { cn } from "@/lib/utils";
// import {
//   Heading1,
//   Heading2,
//   Heading3,
//   Heading4,
//   Title,
// } from "@/components/editor/components/Headings";
// import Paragraph from "@/components/editor/components/Paragraph";
// import { ColumnComponent } from "@/components/editor/components/ColumnComponent";
// import { RecursiveLayout } from "../../editor/RecursiceLayout";
// import { CustomImage } from "@/components/editor/components/ImageComponent";

// const ScaledPreview: React.FC<{ content: ContentItem; isActive: boolean }> = ({
//   content,
//   isActive,
// }) => {
//   const renderContent = (): React.ReactNode => {
//     switch (content.type) {
//       case "heading1":
//         return <Heading1 placeholder={content.placeholder} />;

//       case "heading2":
//         return <Heading2 placeholder={content.placeholder} />;

//       case "heading3":
//         return <Heading3 placeholder={content.placeholder} />;

//       case "heading4":
//         return <Heading4 placeholder={content.placeholder} />;

//       case "title":
//         return <Title placeholder={content.placeholder} />;

//       case "paragraph":
//         return <Paragraph placeholder={content.placeholder} />;

//       case "column":
//         if (Array.isArray(content.content)) {
//           return (
//             <ColumnComponent
//               content={content.content as ContentItem[]}
//               className={content.className}
//               // onEdit={onEdit}
//             />
//           );
//         }
//         return null;

//       case "container":
//         if (Array.isArray(content.content)) {
//           return (
//             <div className={`flex flex-col space-y-4 ${content.className}`}>
//               {(content.content as ContentItem[]).map((item: ContentItem) => (
//                 <RecursiveLayout content={item} key={item.id} />
//               ))}
//             </div>
//           );
//         }

//       case "image":
//         return (
//           <CustomImage
//             src={content.content as string}
//             alt={content.alt || "image"}
//             className={content.className}
//           />
//         );

//       default:
//         return null;
//     }
//   };

//   return (
//     <div
//       className={cn(
//         "w-full aspect-[16/9] rounded-lg overflow-hidden transition-all duration-200 bg-white",
//         isActive
//           ? "ring-2 ring-blue-500 ring-offset-2"
//           : "hover:ring-2 hover:ring-gray-200 hover:ring-offset-2"
//       )}
//     >
//       {renderContent()}
//     </div>
//   );
// };

// const DraggableSlide: React.FC<{
//   slide: Slide;
//   index: number;
//   moveSlide: (dragIndex: number, hoverIndex: number) => void;
// }> = ({ slide, index, moveSlide }) => {
//   const { currentSlide, setCurrentSlide } = useSlideStore();

//   const [{ isDragging }, drag] = useDrag({
//     type: "SLIDE",
//     item: { index },
//     collect: (monitor) => ({
//       isDragging: monitor.isDragging(),
//     }),
//   });

//   const [, drop] = useDrop({
//     accept: "SLIDE",
//     hover(item: { index: number }) {
//       if (!drag) {
//         return;
//       }
//       const dragIndex = item.index;
//       const hoverIndex = index;

//       if (dragIndex === hoverIndex) {
//         return;
//       }

//       moveSlide(dragIndex, hoverIndex);
//       item.index = hoverIndex;
//     },
//   });

//   return (
//     <div
//       ref={(node) => {
//         if (node) {
//           drag(drop(node));
//         }
//       }}
//       className={cn(
//         "relative cursor-pointer group",
//         index === currentSlide ? "before:bg-blue-500" : "before:bg-transparent",
//         isDragging ? "opacity-50" : "opacity-100"
//       )}
//       onClick={() => setCurrentSlide(index)}
//     >
//       <div className="pl-2">
//         <div className="flex items-center justify-between mb-2">
//           <span className="text-xs font-medium text-gray-600">
//             Slide {index + 1}
//           </span>
//         </div>
//         <div>
//           <ScaledPreview
//             content={slide.content}
//             isActive={index === currentSlide}
//           />
//         </div>
//       </div>
//     </div>
//   );
// };

// export const LayoutPreview: React.FC = () => {
//   const { getOrderedSlides, reorderSlide } = useSlideStore();
//   const slides = getOrderedSlides();

//   const moveSlide = (dragIndex: number, hoverIndex: number) => {
//     const draggedSlide = slides[dragIndex];
//     reorderSlide(draggedSlide.id, hoverIndex);
//   };

//   return (
//     <div className="w-64 bg-gray-50 h-full fixed left-0 top-20  border-r overflow-hidden">
//       <ScrollArea className="h-full">
//         <div className="p-4">
//           <div className="flex items-center justify-between mb-6">
//             <h2 className="text-sm font-medium text-gray-500">SLIDES</h2>
//             <span className="text-xs text-gray-400">
//               {slides.length} slides
//             </span>
//           </div>
//           <div className="space-y-4">
//             {slides.map((slide, index) => (
//               <DraggableSlide
//                 key={slide.id}
//                 slide={slide}
//                 index={index}
//                 moveSlide={moveSlide}
//               />
//             ))}
//           </div>
//         </div>
//       </ScrollArea>
//     </div>
//   );
// };
