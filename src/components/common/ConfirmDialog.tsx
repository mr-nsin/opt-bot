import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 animate-overlay" onClick={onCancel} />
      <div className="relative z-50 w-full max-w-md rounded-xl border bg-card p-5 shadow-elevated animate-dialog">
        <button
          onClick={onCancel}
          className="absolute top-3 right-3 h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent transition-colors text-muted-foreground"
        >
          <X className="h-4 w-4" />
        </button>
        <div className="flex items-start gap-3">
          {variant === "destructive" && (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-500/10">
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold">{title}</h3>
            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
              {message}
            </p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant === "destructive" ? "destructive" : "default"}
            size="sm"
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
