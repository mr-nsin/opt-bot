import { useNotificationStore } from "@/stores/notificationStore";
import {
  X,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const colors = {
  success:
    "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  error:
    "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
  warning:
    "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  info: "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
};

export function Toaster() {
  const { toasts, removeToast } = useNotificationStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => {
        const Icon = icons[toast.type];
        return (
          <div
            key={toast.id}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-3 shadow-lg backdrop-blur-sm animate-fade-up",
              colors[toast.type]
            )}
          >
            <Icon className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{toast.title}</p>
              <p className="text-xs opacity-80 mt-0.5">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
