"use client";

import React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenuButton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AvatarImage } from "@radix-ui/react-avatar";
import { NavFooter } from "../app-sidebar/nav-footer";
import { User } from "@prisma/client";
import { ProjectNavMain } from "./project-nav-main";

export function ProjectSidebar({
  user,
  projectId,
  projectTitle,
  ...props
}: { user: User; projectId: string; projectTitle?: string } & React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar
      collapsible="icon"
      defaultOpen={false}
      {...props}
      className="max-w-[212px] bg-background-90"
    >
      <SidebarHeader className="pt-6 px-3 pb-0">
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:text-sidebar-accent-foreground"
        >
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg text-sidebar-primary-foreground">
            <Avatar className="h-10 w-10 rounded-full">
              <AvatarImage src={"/clause.png"} alt={`clause-logo`} />
              <AvatarFallback className="rounded-lg">CL</AvatarFallback>
            </Avatar>
          </div>

          <span className="truncate text-primary text-3xl font-semibold">
            Clause
          </span>
        </SidebarMenuButton>
      </SidebarHeader>
      <SidebarContent className="px-3 mt-10 gap-y-6">
        <ProjectNavMain projectId={projectId} />
        {projectTitle && (
          <div className="px-2 py-2 mt-4">
            <p className="text-sm font-medium text-muted-foreground">Project Name</p>
            <p className="text-base font-semibold text-primary truncate" title={projectTitle}>
              {projectTitle}
            </p>
          </div>
        )}
      </SidebarContent>
      <SidebarFooter>
        <NavFooter prismaUser={user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
