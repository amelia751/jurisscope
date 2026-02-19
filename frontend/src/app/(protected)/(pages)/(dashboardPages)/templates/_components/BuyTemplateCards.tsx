"use client";
import {
  containerVariants,
  itemVariants,
  themes,
  timeAgo,
} from "@/lib/constants";
import { motion } from "framer-motion";
import { Project } from "@prisma/client";
import { ThumbnailPreview } from "@/components/global/project-card/ThumbnailPreview";
import { PrismaUser } from "@/lib/types";

type Props = {
  projects: Project[];
  user: PrismaUser;
};

export const BuyTemplateCard = ({ projects, user }: Props) => {
  return (
    <motion.div
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {projects.map((project, i) => (
        <motion.div
          className={`group w-full flex flex-col gap-y-3 rounded-xl p-3 transition-colors`}
          variants={itemVariants}
          key={i}
        >
          <div
            className="relative aspect-[16/10] overflow-hidden rounded-lg cursor-pointer"
            onClick={() => {}}
          >
            <div className="w-full h-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <p className="text-white font-semibold">Template Preview</p>
            </div>
          </div>
          <div className="w-full">
            <div className="space-y-1">
              <h3 className="font-semibold text-base text-primary line-clamp-1">
                {project.title}
              </h3>
              <div className="flex w-full justify-between items-center gap-2">
                <p className="text-sm text-muted-foreground">
                  {timeAgo(project.createdAt.toString())}
                </p>
                <p className="text-xs text-muted-foreground">
                  Available
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
};
