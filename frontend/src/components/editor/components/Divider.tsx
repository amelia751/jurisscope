import React from 'react';
import { useSlideStore } from '@/store/useSlideStore';
import { cn } from '@/lib/utils';

interface DividerProps {
  className?: string;
}

export const Divider: React.FC<DividerProps> = ({ className }) => {
  const { currentTheme } = useSlideStore();

  return (
    <hr
      className={cn('my-4', className)}
      style={{ borderColor: currentTheme.accentColor }}
    />
  );
};

