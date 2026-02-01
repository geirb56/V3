import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "@/pages/Dashboard";
import Coach from "@/pages/Coach";
import WorkoutDetail from "@/pages/WorkoutDetail";
import Progress from "@/pages/Progress";
import Layout from "@/components/Layout";

function App() {
  return (
    <div className="App min-h-screen bg-background text-foreground">
      <div className="noise-overlay" aria-hidden="true" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="coach" element={<Coach />} />
            <Route path="workout/:id" element={<WorkoutDetail />} />
            <Route path="progress" element={<Progress />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;
