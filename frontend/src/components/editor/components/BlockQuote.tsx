"use client"

import React from 'react';
import { useSlideStore } from '@/store/useSlideStore';
import { cn } from '@/lib/utils';

interface BlockQuoteProps extends React.HTMLAttributes<HTMLQuoteElement> {
  children: React.ReactNode;
  className?: string;
}

export const BlockQuote: React.FC<BlockQuoteProps> = ({ children, className, ...props }) => {
  const { currentTheme } = useSlideStore();

  return (
    <blockquote
      className={cn(
        "pl-4 border-l-4 italic",
        "my-4 py-2",
        "text-gray-700 dark:text-gray-300",
        className
      )}
      style={{
        borderLeftColor: currentTheme.accentColor,
      }}
      {...props}
    >
      {children}
    </blockquote>
  );
};

