import React from "react";

const page = () => {
  return (
    <div className="flex flex-col gap-6 relative">
      <div className="flex justify-between items-center">
        <div className="flex flex-col items-start">
          <h1 className="text-2xl font-semibold dark:text-primary backdrop-blur-lg ">
            Shared
          </h1>
          <p className="text-base font-normal dark:text-secondary">
          Work that you shared, or was shared to you
          </p>
        </div>
      </div>
    </div>
  );
};

export default page;
