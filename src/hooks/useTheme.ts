import { useCallback, useEffect } from "react";
import { useConfigStore } from "@/stores/configStore";

export function useTheme() {
  const { settings, updateSettings } = useConfigStore();
  const theme = settings.theme;

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const newTheme = theme === "dark" ? "light" : "dark";
    updateSettings({ theme: newTheme });
  }, [theme, updateSettings]);

  const setTheme = useCallback(
    (newTheme: "light" | "dark") => {
      updateSettings({ theme: newTheme });
    },
    [updateSettings]
  );

  return { theme, isDark: theme === "dark", toggleTheme, setTheme };
}
