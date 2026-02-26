import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { MarketTicker } from "./MarketTicker";
import { StatusBar } from "./StatusBar";

export function AppShell() {
  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header />
        <MarketTicker />
        <main className="flex-1 overflow-auto p-4">
          <div className="animate-fade-up">
            <Outlet />
          </div>
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
