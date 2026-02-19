import React from 'react';
import { useSlideStore } from '@/store/useSlideStore';
import { cn } from '@/lib/utils';

interface TableOfContentsProps {
  items: string[];
  onItemClick: (id: string) => void;
  className?: string;
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({ items, className }) => {
  const { currentTheme } = useSlideStore();

  return (
    <nav className={cn('space-y-2', className)} style={{ color: currentTheme.fontColor }}>
      {items.map((item,idx) => (
        <div
          key={idx}
          className={cn('cursor-pointer hover:underline')}
          // onClick={() => onItemClick(item)}
        >
          {item}
        </div>
      ))}
    </nav>
  );
};

