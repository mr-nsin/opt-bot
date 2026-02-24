import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
}

/**
 * Pure CSS tooltip - no Radix dependency.
 * Wraps children and shows content on hover.
 */
function Tooltip({ content, children, side = "top", className }: TooltipProps) {
  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <span className="relative inline-flex group">
      {children}
      <span
        className={cn(
          "absolute z-50 px-2.5 py-1.5 rounded-md text-2xs font-medium",
          "bg-foreground text-background shadow-lg",
          "opacity-0 scale-95 pointer-events-none",
          "group-hover:opacity-100 group-hover:scale-100",
          "transition-all duration-150 ease-out",
          "whitespace-nowrap",
          positionClasses[side],
          className
        )}
        role="tooltip"
      >
        {content}
      </span>
    </span>
  );
}

export { Tooltip };
