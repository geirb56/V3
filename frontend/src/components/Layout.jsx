import { Outlet, NavLink, useLocation } from "react-router-dom";
import { Activity, MessageSquare, BarChart3, Home, Settings, Compass, CalendarDays } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";

export const Layout = () => {
  const location = useLocation();
  const { t } = useLanguage();

  const navItems = [
    { path: "/", icon: Home, labelKey: "nav.dashboard" },
    { path: "/digest", icon: CalendarDays, labelKey: "nav.digest" },
    { path: "/coach", icon: MessageSquare, labelKey: "nav.coach" },
    { path: "/progress", icon: BarChart3, labelKey: "nav.progress" },
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

        <div className="pt-6 border-t border-border mt-auto">
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
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
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
    </div>
  );
};

export default Layout;
