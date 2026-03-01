import { memo } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { StatusBar } from "./StatusBar";

function AppShellInner() {
  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-auto p-4 min-h-0 overflow-x-hidden">
          <Outlet />
        </main>
        <StatusBar />
      </div>
    </div>
  );
}

export const AppShell = memo(AppShellInner);
