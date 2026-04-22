import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { NotificationsProvider } from "@/contexts/NotificationsContext";
import Navbar from "@/components/Navbar";
import Index from "./pages/Index";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Resources from "./pages/Resources";
import MoodTracker from "./pages/MoodTracker";
import Journal from "./pages/Journal";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
    <QueryClientProvider client={queryClient}>
      <NotificationsProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <Navbar />
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/mood" element={<MoodTracker />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/login" element={<Login />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
      </NotificationsProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
