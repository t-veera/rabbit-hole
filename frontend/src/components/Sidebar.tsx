import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Notification } from "../types";
import { applyTheme, getStoredTheme, resolvedTheme, type ThemeChoice } from "../theme";

interface Props {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

function FeedIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 4v16" />
      <path d="M4 4a16 16 0 0116 16" />
      <path d="M4 11a9 9 0 019 9" />
      <circle cx="5.5" cy="18.5" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function SearchNavIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}

function PeopleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.8 19c0-3.4 2.8-6 6.2-6s6.2 2.6 6.2 6" />
      <path d="M15.5 3.5a3.2 3.2 0 010 9" />
      <path d="M16.8 13c3 .3 5.4 2.8 5.4 6" />
    </svg>
  );
}

function JournalismIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 5h13a3 3 0 013 3v11H7a3 3 0 01-3-3V5z" />
      <path d="M17 19V8h3" />
      <path d="M7.5 9h6M7.5 12.5h6M7.5 16h4" />
    </svg>
  );
}

function LibraryIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h4v16H4z" />
      <path d="M10 4h4v16h-4z" />
      <path d="M16.3 4.6l3.6 15.5-3.9.9L12.4 5.5z" />
    </svg>
  );
}

function ListsIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M9 6h12M9 12h12M9 18h12" />
      <path d="M4 6h.01M4 12h.01M4 18h.01" strokeWidth="2.6" />
    </svg>
  );
}

function NotesIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 3h10l4 4v14H5z" />
      <path d="M15 3v4h4" />
      <path d="M8.5 12.5h7M8.5 16h5" />
    </svg>
  );
}

function GraphIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="6" cy="6" r="2.4" />
      <circle cx="18" cy="6" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M8 7.2L10 16M16 7.2L14 16M8.4 6h7.2" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13.5a1.7 1.7 0 000-3l1.3-1.9-2.1-2.1-1.9 1.3a1.7 1.7 0 00-3 0L12 5.6l-1.7 1.2a1.7 1.7 0 00-3 0L5.4 5.5 3.3 7.6l1.3 1.9a1.7 1.7 0 000 3l-1.3 1.9 2.1 2.1 1.9-1.3a1.7 1.7 0 003 0l1.7 1.2 1.7-1.2a1.7 1.7 0 003 0l1.9 1.3 2.1-2.1z" />
    </svg>
  );
}

const LINKS = [
  { to: "/", label: "Feed", end: true, Icon: FeedIcon },
  { to: "/search", label: "Search", Icon: SearchNavIcon },
  { to: "/people", label: "People", Icon: PeopleIcon },
  { to: "/journalism", label: "Journalism", Icon: JournalismIcon },
  { to: "/library", label: "Library Search", Icon: LibraryIcon },
  { to: "/lists", label: "Lists", Icon: ListsIcon },
  { to: "/notes", label: "Notes", Icon: NotesIcon },
  { to: "/graph", label: "Graph", Icon: GraphIcon },
  { to: "/settings", label: "Settings", Icon: SettingsIcon },
];

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8L6 18M18 6l1.8-1.8" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.7 14.1A8.6 8.6 0 019.9 3.3a.6.6 0 00-.7-.8A9.8 9.8 0 1021.5 14.8a.6.6 0 00-.8-.7z" />
    </svg>
  );
}

function CollapseIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: collapsed ? "rotate(180deg)" : undefined }}
    >
      <path d="M15 5l-7 7 7 7" />
      <path d="M20 5v14" />
    </svg>
  );
}

export default function Sidebar({ collapsed, onToggleCollapse }: Props) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [themeChoice, setThemeChoice] = useState<ThemeChoice>(getStoredTheme());

  useEffect(() => {
    function load() {
      api.get<Notification[]>("/api/topics/notifications").then(setNotifications).catch(() => {});
    }
    load();
    window.addEventListener("rh:notifications-refresh", load);
    return () => window.removeEventListener("rh:notifications-refresh", load);
  }, []);

  const totalNew = notifications.reduce((sum, n) => sum + n.new_count, 0);

  function toggleTheme() {
    const next = resolvedTheme() === "dark" ? "light" : "dark";
    setThemeChoice(next);
    applyTheme(next);
  }

  return (
    <aside className={"sidebar" + (collapsed ? " collapsed" : "")}>
      <div className="masthead">
        <div className="masthead-row">
          {/* Logo mark goes here — "Rabbit Hole" wordmark is the placeholder until then. */}
          {!collapsed && <div className="sidebar-title">Rabbit Hole</div>}
          {collapsed && <div className="sidebar-title-collapsed">R</div>}
        </div>
      </div>

      <div className="sidebar-top-controls">
        <button className="theme-toggle-top" onClick={toggleTheme} title={resolvedTheme() === "dark" ? "Switch to light" : "Switch to dark"}>
          {resolvedTheme() === "dark" ? <MoonIcon /> : <SunIcon />}
          {!collapsed && <span>{resolvedTheme() === "dark" ? "Dark" : "Light"}</span>}
          {!collapsed && themeChoice === "system" && <span style={{ opacity: 0.6 }}>(system)</span>}
        </button>

        <button className="sidebar-collapse-toggle" onClick={onToggleCollapse} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          <CollapseIcon collapsed={collapsed} />
        </button>
      </div>

      <nav className="sidebar-nav">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
            title={collapsed ? link.label : undefined}
          >
            {collapsed ? (
              <span className="sidebar-link-icon">
                <link.Icon />
              </span>
            ) : (
              <span className="sidebar-link-label">{link.label}</span>
            )}
            {link.to === "/" && totalNew > 0 && <span className="badge">{totalNew}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
