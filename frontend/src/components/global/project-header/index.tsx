"use client";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@radix-ui/react-separator";
import React from "react";
import { ThemeSwitcher } from "../mode-toggle";
import SearchBar from "../upper-info-bar/upper-info-searchbar";
import { User } from "@prisma/client";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

const ProjectHeader = ({ user }: { user: User }) => {
  const router = useRouter();

  return (
    <header className="sticky top-0 z-[10] flex shrink-0 flex-wrap items-center gap-2 border-b bg-background p-4 justify-between">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />

      <div className="w-full max-w-[95%] flex items-center justify-between gap-4 flex-wrap">
        {/* Search */}
        <SearchBar />
        {/* Mode Toggle */}
        <ThemeSwitcher />
        <div className="flex flex-wrap gap-4 items-center justify-end">
          <Button
            size={"lg"}
            className="rounded-lg font-semibold"
            onClick={() => router.push("/dashboard")}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    </header>
  );
};

export default ProjectHeader;
