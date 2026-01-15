/**
 * Pipeline One - HelpIcon component
 * Standardized help trigger with tooltip
 */

import { ReactNode } from 'react';
import { QuestionMarkCircleIcon } from '@heroicons/react/24/outline';
import { Tooltip } from './Tooltip';

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface HelpIconProps {
  content: ReactNode;
  position?: TooltipPosition;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

export function HelpIcon({
  content,
  position = 'top',
  size = 'sm',
  className = '',
}: HelpIconProps) {
  return (
    <Tooltip content={content} position={position}>
      <button
        type="button"
        className={`text-secondary-400 hover:text-secondary-200 focus:outline-none focus:text-secondary-200 transition-colors ${className}`}
        aria-label="Help"
        tabIndex={0}
      >
        <QuestionMarkCircleIcon className={sizeClasses[size]} />
      </button>
    </Tooltip>
  );
}

// Labeled help icon - combines a label with help icon
interface LabelWithHelpProps {
  label: string;
  helpContent: ReactNode;
  required?: boolean;
  className?: string;
}

export function LabelWithHelp({
  label,
  helpContent,
  required = false,
  className = '',
}: LabelWithHelpProps) {
  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      <span className="text-sm font-medium text-secondary-200">
        {label}
        {required && <span className="text-accent-500 ml-0.5">*</span>}
      </span>
      <HelpIcon content={helpContent} size="sm" />
    </div>
  );
}
