import React, { useState } from 'react';
import { useSlideStore } from '@/store/useSlideStore';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

interface CustomButtonProps {
  text: string;
  href: string;
  bgColor: string;
  isTransparent: boolean;
  onChange: (newProps: Partial<CustomButtonProps>) => void;
  className?: string;
}

export const CustomButton: React.FC<CustomButtonProps> = ({ text, href, bgColor, isTransparent, onChange, className }) => {
  const { currentTheme } = useSlideStore();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          className={className}
          style={{
            backgroundColor: isTransparent ? 'transparent' : bgColor,
            color: currentTheme.fontColor,
            border: isTransparent ? `1px solid ${currentTheme.fontColor}` : 'none',
          }}
        >
          {text}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="text">Button Text</Label>
            <Input
              id="text"
              value={text}
              onChange={(e) => onChange({ text: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="href">Redirect URL</Label>
            <Input
              id="href"
              value={href}
              onChange={(e) => onChange({ href: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="bgColor">Background Color</Label>
            <Input
              id="bgColor"
              type="color"
              value={bgColor}
              onChange={(e) => onChange({ bgColor: e.target.value })}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="transparent"
              checked={isTransparent}
              onCheckedChange={(checked) => onChange({ isTransparent: checked })}
            />
            <Label htmlFor="transparent">Transparent Background</Label>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

