import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { LanguageProvider } from "@/context/LanguageContext";
import Dashboard from "@/pages/Dashboard";
import Coach from "@/pages/Coach";
import WorkoutDetail from "@/pages/WorkoutDetail";
import Progress from "@/pages/Progress";
import Guidance from "@/pages/Guidance";
import Digest from "@/pages/Digest";
import Settings from "@/pages/Settings";
import Layout from "@/components/Layout";

function App() {
  return (
    <LanguageProvider>
      <div className="App min-h-screen bg-background text-foreground">
        <div className="noise-overlay" aria-hidden="true" />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="coach" element={<Coach />} />
              <Route path="workout/:id" element={<WorkoutDetail />} />
              <Route path="progress" element={<Progress />} />
              <Route path="guidance" element={<Guidance />} />
              <Route path="digest" element={<Digest />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </div>
    </LanguageProvider>
  );
}

export default App;
