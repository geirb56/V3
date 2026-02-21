import { useState, useEffect } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import { Activity, MessageSquare, BarChart3, Home, Settings, Compass, CalendarDays, Crown, CreditCard } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import { useAutoSync } from "@/hooks/useAutoSync";
import ChatCoach from "@/components/ChatCoach";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const Layout = () => {
  const location = useLocation();
  const { t } = useLanguage();
  const [chatOpen, setChatOpen] = useState(false);
  const [subscriptionTier, setSubscriptionTier] = useState("free");
  const [tierName, setTierName] = useState("Gratuit");
  
  // Auto-sync Strava data on startup
  useAutoSync();

  // Check subscription status
  useEffect(() => {
    const checkSubscription = async () => {
      try {
        const res = await axios.get(`${API}/subscription/status?user_id=default`);
        setSubscriptionTier(res.data.tier || "free");
        setTierName(res.data.tier_name || "Gratuit");
      } catch (err) {
        console.error("Error checking subscription:", err);
      }
    };
    checkSubscription();
  }, []);

  const isPremium = subscriptionTier !== "free";

  const navItems = [
    { path: "/", icon: Home, labelKey: "nav.dashboard" },
    { path: "/digest", icon: CalendarDays, labelKey: "nav.digest" },
    { path: "/progress", icon: BarChart3, labelKey: "nav.progress" },
    { path: "/subscription", icon: CreditCard, labelKey: "nav.subscription" },
    { path: "/settings", icon: Settings, labelKey: "nav.settings" },
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-64 border-r border-border bg-background p-6">
        <div className="mb-10">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-primary" />
            <span className="font-heading text-xl uppercase tracking-tight font-bold">
              CardioCoach
            </span>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.labelKey.split(".")[1]}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm font-mono uppercase tracking-wider transition-colors ${
                  isActive
                    ? "text-primary border-l-2 border-primary bg-muted/50"
                    : "text-muted-foreground hover:text-foreground border-l-2 border-transparent"
                }`
              }
            >
              <item.icon className="w-4 h-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>

        {/* Chat Coach Button - Desktop */}
        <button
          onClick={() => setChatOpen(true)}
          data-testid="chat-coach-btn-desktop"
          className={`flex items-center gap-3 px-4 py-3 text-sm font-mono uppercase tracking-wider transition-all mt-2 rounded-lg ${
            isPremium 
              ? "bg-gradient-to-r from-amber-500/10 to-orange-500/10 text-amber-600 hover:from-amber-500/20 hover:to-orange-500/20"
              : "bg-muted/50 text-muted-foreground hover:bg-muted"
          }`}
        >
          <Crown className={`w-4 h-4 ${isPremium ? "text-amber-500" : ""}`} />
          Chat Coach
          {isPremium && (
            <span className="ml-auto text-[8px] bg-amber-500 text-white px-1.5 py-0.5 rounded-full">PRO</span>
          )}
        </button>

        <div className="pt-6 border-t border-border mt-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {t("nav.tagline")}
          </p>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="md:hidden flex items-center justify-between p-4 border-b border-border bg-background">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <span className="font-heading text-lg uppercase tracking-tight font-bold">
            CardioCoach
          </span>
        </div>
        {/* Chat button mobile header */}
        <button
          onClick={() => setChatOpen(true)}
          data-testid="chat-coach-btn-mobile"
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium ${
            isPremium 
              ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white"
              : "bg-muted text-muted-foreground"
          }`}
        >
          <Crown className="w-3.5 h-3.5" />
          <span className="hidden xs:inline">Chat</span>
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-auto pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 flex items-center justify-around p-2 border-t border-border bg-background/95 backdrop-blur-sm">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              data-testid={`mobile-nav-${item.labelKey.split(".")[1]}`}
              className={`flex flex-col items-center gap-1 p-2 ${
                isActive ? "text-primary" : "text-muted-foreground"
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-mono text-[9px] uppercase tracking-wider">
                {t(item.labelKey)}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* Chat Coach Overlay */}
      <ChatCoach 
        isOpen={chatOpen} 
        onClose={() => setChatOpen(false)} 
        userId="default"
      />
    </div>
  );
};

export default Layout;
