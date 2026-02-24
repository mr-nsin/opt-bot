import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { AlertTriangle, Info, CheckCircle2, XCircle, Zap } from "lucide-react";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm flex items-start gap-3 [&>svg]:shrink-0 [&>svg]:mt-0.5",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground border-border",
        info: "bg-blue-500/5 text-blue-700 dark:text-blue-400 border-blue-500/20 [&>svg]:text-blue-500",
        success: "bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 [&>svg]:text-emerald-500",
        warning: "bg-amber-500/5 text-amber-700 dark:text-amber-400 border-amber-500/20 [&>svg]:text-amber-500",
        destructive: "bg-red-500/5 text-red-700 dark:text-red-400 border-red-500/20 [&>svg]:text-red-500",
        signal: "bg-violet-500/5 text-violet-700 dark:text-violet-400 border-violet-500/20 [&>svg]:text-violet-500",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

const iconMap = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  destructive: XCircle,
  signal: Zap,
};

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  icon?: React.ReactNode;
}

function Alert({ className, variant = "default", icon, children, ...props }: AlertProps) {
  const IconComponent = iconMap[variant ?? "default"];

  return (
    <div className={cn(alertVariants({ variant }), className)} role="alert" {...props}>
      {icon ?? <IconComponent className="h-4 w-4" />}
      <div className="flex-1 space-y-1">{children}</div>
    </div>
  );
}

function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm font-semibold leading-none", className)} {...props} />;
}

function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs opacity-80 leading-relaxed", className)} {...props} />;
}

export { Alert, AlertTitle, AlertDescription, alertVariants };
