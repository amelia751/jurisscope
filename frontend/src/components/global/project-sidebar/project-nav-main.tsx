"use client";
import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Search, FolderOpen, Table2 } from "lucide-react";

export function ProjectNavMain({ projectId }: { projectId: string }) {
  const pathname = usePathname();

  const items = [
    {
      title: "Discover",
      url: `/project/${projectId}`,
      icon: Search,
    },
    {
      title: "Vault",
      url: `/project/${projectId}/vault`,
      icon: FolderOpen,
    },
    {
      title: "Table",
      url: `/project/${projectId}/table`,
      icon: Table2,
    },
  ];

  return (
    <SidebarGroup className="p-0">
      <SidebarMenu>
        {items.map((item, idx) => {
          const isActive = pathname === item.url;
          return (
            <SidebarMenuItem key={idx}>
              <SidebarMenuButton
                asChild
                tooltip={item.title}
                className={`${isActive && "bg-background-80"}`}
              >
                <Link
                  href={item.url}
                  className={`text-lg ${isActive && "font-bold"}`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          );
        })}
      </SidebarMenu>
    </SidebarGroup>
  );
}
