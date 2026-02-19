"use client";

import React from "react";
import { LayoutTemplate, Type, Palette } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { LayoutChooser } from "./tabs/LayoutChooser";
import { useSlideStore } from "@/store/useSlideStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeChooser } from "./tabs/ThemeChooser";
import { component } from "@/lib/constants";
import { ComponentCard } from "./tabs/components-tab/ComponentPreview";

// const TextComponent = ({ item }: { item: TextComponentItem }) => {
//   const { currentTheme } = useSlideStore();

//   const [{ isDragging }, drag] = useDrag({
//     type: "CONTENT_ITEM",
//     item:  item,
//     collect: (monitor) => ({
//       isDragging: !!monitor.isDragging(),
//     }),
//   });

//   return (
//     <Button
//       ref={drag as unknown as React.LegacyRef<HTMLButtonElement>}
//       variant="ghost"
//       className="w-full justify-start"
//       style={{
//         color: currentTheme.fontColor,
//         opacity: isDragging ? 0.5 : 1,
//       }}
//     >
//       {item.label}
//     </Button>
//   );
// };

const EditorSidebar = () => {
  const { currentTheme } = useSlideStore();

  return (
    <div className="fixed top-1/2 right-0 transform -translate-y-1/2 z-10">
      <div className="rounded-xl border-r-0 border border-background-70 shadow-lg p-2 flex flex-col items-center space-y-4">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-full"
            >
              <LayoutTemplate className="h-5 w-5" />
              <span className="sr-only">Choose Layout</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent
            side="left"
            align="center"
            className="w-[480px] p-0"
          >
            <LayoutChooser />
          </PopoverContent>
        </Popover>

        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-full"
            >
              <Type className="h-5 w-5" />
              <span className="sr-only">Add Text</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent
            side="left"
            align="center"
             className="w-[480px] p-0"
            style={{
              backgroundColor: currentTheme.backgroundColor,
              color: currentTheme.fontColor,
            }}
          >
            <ScrollArea className="h-[400px]">
              <div className="p-4 fle flex-col space-y-6">
                {component.map((group, idx) => (
                  <div className="space-y-2" key={idx}>
                    <h3 className="text-sm font-medium text-muted-foreground px-1">
                      {group.name}
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      {group.components.map((item) => (
                        <ComponentCard key={item.componentType} item={item} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </PopoverContent>
        </Popover>

        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-full"
            >
              <Palette className="h-5 w-5" />
              <span className="sr-only">Change Style</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent
            side="left"
            align="center"
            className="w-80 "
          >
            <ThemeChooser />
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
};

export default EditorSidebar;
