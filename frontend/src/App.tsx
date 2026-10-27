import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Topbar } from "./components/layout/Topbar";
import { ToastProvider } from "./components/ui";
import { Dashboard } from "./pages/Dashboard";
import { Settings } from "./pages/Settings";
import { LiveMap } from "./pages/Livemap";
import { ModelEvaluation } from "./pages/ModelEvaluation";
import { LoginPage } from "./pages/Login";
import { ThemeProvider } from "./lib/ThemeContext";
import { AuthProvider, useAuth } from "./lib/AuthContext";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 3000 } },
});

function AppShell() {
  const { isAuthenticated } = useAuth();
  const [page, setPage] = useState("dashboard");

  if (!isAuthenticated) {
    return (
      <ToastProvider>
        <LoginPage />
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <div className="flex h-screen flex-col bg-base">
        <Topbar page={page} onNavigate={setPage} />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto w-full max-w-canvas p-4 md:p-6">
            {page === "dashboard" && <Dashboard />}
            {page === "map" && <LiveMap />}
            {page === "model" && <ModelEvaluation />}
            {page === "settings" && <Settings />}
          </div>
        </main>
      </div>
    </ToastProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <AppShell />
        </QueryClientProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}
