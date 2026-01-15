/**
 * Pipeline One - Reusable Tooltip component
 * Provides contextual help information on hover
 */

import { ReactNode, useState, useRef, useEffect } from 'react';

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: TooltipPosition;
  delay?: number;
  maxWidth?: number;
  className?: string;
}

const positionClasses: Record<TooltipPosition, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

const arrowClasses: Record<TooltipPosition, string> = {
  top: 'top-full left-1/2 -translate-x-1/2 border-t-secondary-700 border-x-transparent border-b-transparent',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-secondary-700 border-x-transparent border-t-transparent',
  left: 'left-full top-1/2 -translate-y-1/2 border-l-secondary-700 border-y-transparent border-r-transparent',
  right: 'right-full top-1/2 -translate-y-1/2 border-r-secondary-700 border-y-transparent border-l-transparent',
};

export function Tooltip({
  content,
  children,
  position = 'top',
  delay = 200,
  maxWidth = 280,
  className = '',
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      className={`relative inline-flex ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleMouseEnter}
      onBlur={handleMouseLeave}
    >
      {children}
      {isVisible && content && (
        <div
          className={`absolute z-50 ${positionClasses[position]}`}
          role="tooltip"
        >
          <div
            className="bg-secondary-700 text-secondary-100 text-sm px-3 py-2 rounded-lg shadow-lg"
            style={{ maxWidth }}
          >
            {content}
          </div>
          {/* Arrow */}
          <div
            className={`absolute border-4 ${arrowClasses[position]}`}
          />
        </div>
      )}
    </div>
  );
}

// Simplified tooltip for string-only content
interface SimpleTooltipProps {
  text: string;
  children: ReactNode;
  position?: TooltipPosition;
}

export function SimpleTooltip({ text, children, position = 'top' }: SimpleTooltipProps) {
  return (
    <Tooltip content={text} position={position}>
      {children}
    </Tooltip>
  );
}
