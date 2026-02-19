import { WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useSlideStore } from "@/store/useSlideStore";

export default function SellTemplate() {
  const { currentTheme, project } = useSlideStore();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon" style={{
           backgroundColor: currentTheme.backgroundColor,
        }}>
          <WalletCards className="h-6 w-6" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Template Sharing</h2>
          <p className="text-sm text-muted-foreground">
            Template sharing and marketplace features have been disabled.
          </p>
          {project?.isSellable && (
            <p className="text-xs text-green-600">
              This template was previously marked as sellable.
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
