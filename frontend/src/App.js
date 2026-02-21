import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { LanguageProvider } from "@/context/LanguageContext";
import { WebLLMProvider } from "@/context/WebLLMContext";
import WebLLMBanners from "@/components/WebLLMBanners";
import Dashboard from "@/pages/Dashboard";
import WorkoutDetail from "@/pages/WorkoutDetail";
import DetailedAnalysis from "@/pages/DetailedAnalysis";
import Progress from "@/pages/Progress";
import Guidance from "@/pages/Guidance";
import Digest from "@/pages/Digest";
import Settings from "@/pages/Settings";
import Subscription from "@/pages/Subscription";
import Layout from "@/components/Layout";

function App() {
  return (
    <LanguageProvider>
      <WebLLMProvider>
        <div className="App min-h-screen bg-background text-foreground">
          <div className="noise-overlay" aria-hidden="true" />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="workout/:id" element={<WorkoutDetail />} />
                <Route path="workout/:id/analysis" element={<DetailedAnalysis />} />
                <Route path="progress" element={<Progress />} />
                <Route path="guidance" element={<Guidance />} />
                <Route path="digest" element={<Digest />} />
                <Route path="settings" element={<Settings />} />
                <Route path="subscription" element={<Subscription />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <WebLLMBanners />
          <Toaster position="bottom-right" />
        </div>
      </WebLLMProvider>
    </LanguageProvider>
  );
}

export default App;
