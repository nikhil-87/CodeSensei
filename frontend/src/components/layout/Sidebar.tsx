import {
  Activity,
  Boxes,
  Compass,
  GitGraph,
  Layers,
  MessageCircle,
  ScanSearch,
  Skull,
  Star,
  Workflow,
} from "lucide-react";
import { NavLink, useParams } from "react-router-dom";

import { Logo } from "@/components/common/Logo";
import { cn } from "@/lib/format";
import { config } from "@/lib/config";
import { useMe } from "@/hooks/useAuth";
import { useUiStore } from "@/store/uiStore";

const REPO_NAV = [
  { to: "overview", icon: Activity, label: "Overview" },
  { to: "graph", icon: GitGraph, label: "Dependencies" },
  { to: "complexity", icon: Workflow, label: "Complexity" },
  { to: "dead-code", icon: Skull, label: "Dead code" },
  { to: "architecture", icon: Layers, label: "Architecture" },
  { to: "impact", icon: ScanSearch, label: "Impact" },
  { to: "chat", icon: MessageCircle, label: "AI assistant" },
];

export function Sidebar({
  mobile = false,
  onNavigate,
}: {
  /** When rendered inside the mobile drawer, always show full labels. */
  mobile?: boolean;
  /** Called after a nav link is tapped (used to auto-close the mobile drawer). */
  onNavigate?: () => void;
} = {}) {
  const collapsedDesktop = useUiStore((s) => s.sidebarCollapsed);
  const collapsed = mobile ? false : collapsedDesktop;
  const params = useParams<{ repositoryId?: string }>();
  const repoId = params.repositoryId;
  const { isAuthenticated } = useMe();

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-ink-200 bg-surface",
        mobile ? "w-full" : "shrink-0 transition-[width]",
        !mobile && (collapsed ? "w-16" : "w-64"),
      )}
    >
      <NavLink
        to="/"
        onClick={onNavigate}
        className="flex h-14 items-center gap-2 border-b border-ink-100 px-4 font-semibold text-ink-900"
      >
        <Logo className="h-8 w-8 text-accent-600" />
        {!collapsed && <span>{config.app.name}</span>}
      </NavLink>

      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <NavGroup label={collapsed ? null : "Workspace"}>
          {isAuthenticated && (
            <NavItem icon={Boxes} label="Repositories" to="/" end collapsed={collapsed} onNavigate={onNavigate} />
          )}
          <NavItem icon={Compass} label="Discover" to="/discover" collapsed={collapsed} onNavigate={onNavigate} />
          {isAuthenticated && (
            <NavItem icon={Star} label="Your stars" to="/stars" collapsed={collapsed} onNavigate={onNavigate} />
          )}
        </NavGroup>

        {repoId && (
          <NavGroup label={collapsed ? null : "Current repository"}>
            {REPO_NAV.map(({ to, icon, label }) => (
              <NavItem
                key={to}
                icon={icon}
                label={label}
                to={`/repos/${repoId}/${to}`}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            ))}
          </NavGroup>
        )}
      </nav>

      <footer className="border-t border-ink-100 p-3 text-xs text-ink-400">
        {collapsed ? "v" : `Version ${config.app.version}`}
      </footer>
    </aside>
  );
}

function NavGroup({
  label,
  children,
}: {
  label: string | null;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-4">
      {label && (
        <h4 className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wider text-ink-400">
          {label}
        </h4>
      )}
      <ul className="flex flex-col gap-0.5">{children}</ul>
    </div>
  );
}

function NavItem({
  icon: Icon,
  label,
  to,
  end,
  collapsed,
  onNavigate,
}: {
  icon: typeof Boxes;
  label: string;
  to: string;
  end?: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <li>
      <NavLink
        to={to}
        end={end}
        onClick={onNavigate}
        title={collapsed ? label : undefined}
        className={({ isActive }) =>
          cn(
            "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium",
            isActive
              ? "bg-accent-50 text-accent-700"
              : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
          )
        }
      >
        <Icon className="h-4 w-4" />
        {!collapsed && <span>{label}</span>}
      </NavLink>
    </li>
  );
}
