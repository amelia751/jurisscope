import { getSellableProjects } from "@/actions/project";
import { NotFound } from "@/components/global/not-found";
import React from "react";
import { BuyTemplateCard } from "./_components/BuyTemplateCards";
import { onAuthenticateUser } from "@/actions/user";
import { PrismaUser } from "@/lib/types";

const page = async () => {
  const sellableProducts = await getSellableProjects();
  const checkUser = await onAuthenticateUser();
  return (
    <div className="flex flex-col gap-6 relative">
      <div className="flex justify-between items-center">
        <div className="flex flex-col items-start">
          <h1 className="text-2xl font-semibold dark:text-primary backdrop-blur-lg ">
            Templates
          </h1>
          <p className="text-base font-normal dark:text-secondary">
            All of your work in one place 
          </p>
        </div>
      </div>

      {/* Projects */}
      {sellableProducts.data && sellableProducts?.data?.length > 0 && checkUser.user ? (
        <BuyTemplateCard
          projects={sellableProducts.data}
          user={checkUser.user as PrismaUser}
        />
      ) : (
        <NotFound />
      )}
    </div>
  );
};

export default page;
