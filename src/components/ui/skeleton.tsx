import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Render as a circle (e.g. for avatars/icons) */
  circle?: boolean;
}

function Skeleton({ className, circle, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "skeleton rounded-md",
        circle && "rounded-full",
        className
      )}
      {...props}
    />
  );
}

/** Pre-built skeleton for a StatCard */
function SkeletonStatCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-3.5 rounded-xl border border-border/70 bg-card space-y-2", className)}>
      <div className="flex items-start justify-between">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-7 w-7 rounded-md" />
      </div>
      <Skeleton className="h-7 w-24" />
      <Skeleton className="h-3 w-12" />
    </div>
  );
}

/** Pre-built skeleton for a Card section */
function SkeletonCard({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={cn("rounded-xl border border-border/70 bg-card p-4 space-y-3", className)}>
      <Skeleton className="h-4 w-32" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-3 w-full" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  );
}

/** Pre-built skeleton for a table row */
function SkeletonTableRow({ columns = 8, className }: { columns?: number; className?: string }) {
  return (
    <tr className={cn("border-b", className)}>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-2.5 pr-3">
          <Skeleton className="h-3.5 w-full" style={{ width: `${60 + Math.random() * 40}%` }} />
        </td>
      ))}
    </tr>
  );
}

export { Skeleton, SkeletonStatCard, SkeletonCard, SkeletonTableRow };
