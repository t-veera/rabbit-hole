import { useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Feed from "./pages/Feed";
import Journalism from "./pages/Journalism";
import Search from "./pages/Search";
import PaperDetail from "./pages/PaperDetail";
import ArticleDetail from "./pages/ArticleDetail";
import ResearcherProfile from "./pages/ResearcherProfile";
import Lists from "./pages/Lists";
import ListDetail from "./pages/ListDetail";
import Notes from "./pages/Notes";
import Graph from "./pages/Graph";
import Settings from "./pages/Settings";
import Library from "./pages/Library";
import SplitView from "./pages/SplitView";
import People from "./pages/People";

// Split view and the graph both need the full screen width to be useful —
// two reading panes or a force-directed graph inside a narrow reading
// column just cramps them for no reason the way a fixed-width column
// helps a plain list view. Paper/article detail pages join them since
// their body text (.article-body) is intentionally unconstrained too —
// reads like a longform article, not a cramped centered column.
function isWideRoute(pathname: string): boolean {
  return (
    pathname === "/split" ||
    pathname === "/graph" ||
    pathname.startsWith("/papers/") ||
    pathname.startsWith("/articles/")
  );
}

const SIDEBAR_COLLAPSE_KEY = "rabbit-hole-sidebar-collapsed";

function getStoredCollapse(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === "true";
  } catch {
    return false;
  }
}

export default function App() {
  const location = useLocation();
  const isWide = isWideRoute(location.pathname);
  const isSplit = location.pathname === "/split";
  const [collapsed, setCollapsed] = useState<boolean>(getStoredCollapse);

  function toggleCollapse() {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSE_KEY, String(next));
      } catch {
        // ignore — per-viewer convenience only
      }
      return next;
    });
  }

  return (
    <div className={"app-shell" + (isSplit ? " split-mode" : "") + (collapsed ? " sidebar-collapsed" : "")}>
      <Sidebar collapsed={collapsed || isSplit} onToggleCollapse={toggleCollapse} />
      <main className={isWide ? "main-wide" : "main"}>
        <Routes>
          <Route path="/" element={<Feed />} />
          <Route path="/search" element={<Search />} />
          <Route path="/people" element={<People />} />
          <Route path="/journalism" element={<Journalism />} />
          <Route path="/library" element={<Library />} />
          <Route path="/papers/:id" element={<PaperDetail />} />
          <Route path="/articles/:id" element={<ArticleDetail />} />
          <Route path="/researchers/:id" element={<ResearcherProfile />} />
          <Route path="/lists" element={<Lists />} />
          <Route path="/lists/:id" element={<ListDetail />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/split" element={<SplitView />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
