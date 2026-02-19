import { Rabbit } from "lucide-react";

export const NotFound = () => {
  return (
    <div className="flex flex-col min-h-[70vh] w-full justify-center items-center gap-6">
      <Rabbit className="w-32 h-32 text-gray-400 dark:text-gray-600" strokeWidth={1.5} />
      <div className="flex flex-col items-center justify-center text-center">
        <p className="text-base font-normal text-secondary">
          You don't have any projects yet
        </p>
      </div>
    </div>
  );
};
