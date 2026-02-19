import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@radix-ui/react-separator";
import React from "react";
import { ThemeSwitcher } from "../mode-toggle";
import SearchBar from "./upper-info-searchbar";
import NewProjectButton from "./new-project-button";
import { User } from "@prisma/client";

const UpperInfoBar = ({user}:{user:User}) => {
  return (
    <header className="sticky top-0 z-[10] flex shrink-0 flex-wrap items-center gap-2 border-b bg-background p-4 justify-between">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />

      <div className="w-full max-w-[95%] flex items-center justify-between gap-4 flex-wrap">
        {/* Search */}
        <SearchBar/>
        {/* Mode Toggle */}
        <ThemeSwitcher />
        <div className="flex flex-wrap gap-4 items-center justify-end">
         <NewProjectButton user={user}/>
        </div>
      </div>
    </header>
  );
};

export default UpperInfoBar;
