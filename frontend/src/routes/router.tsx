import { Navigate, createBrowserRouter } from "react-router-dom";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { AIAssistantPage } from "@/pages/AIAssistantPage";
import { ArchitecturePage } from "@/pages/ArchitecturePage";
import { ComplexityPage } from "@/pages/ComplexityPage";
import { DeadCodePage } from "@/pages/DeadCodePage";
import { DependencyGraphPage } from "@/pages/DependencyGraphPage";
import { DiscoverPage } from "@/pages/DiscoverPage";
import { ImpactAnalysisPage } from "@/pages/ImpactAnalysisPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RepositoryAnalysesPage } from "@/pages/RepositoryAnalysesPage";
import { RepositoryDashboardPage } from "@/pages/RepositoryDashboardPage";
import { RepositoryListPage } from "@/pages/RepositoryListPage";
import { StarredPage } from "@/pages/StarredPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <AppShell />,
    children: [
      {
        index: true,
        element: (
          <RequireAuth>
            <RepositoryListPage />
          </RequireAuth>
        ),
      },
      // Public, anonymous-friendly social surfaces.
      { path: "discover", element: <DiscoverPage /> },
      { path: "discover/r", element: <RepositoryAnalysesPage /> },
      { path: "u/:username", element: <ProfilePage /> },
      {
        path: "stars",
        element: (
          <RequireAuth>
            <StarredPage />
          </RequireAuth>
        ),
      },
      {
        path: "repos/:repositoryId",
        children: [
          { index: true, element: <Navigate to="overview" replace /> },
          { path: "overview", element: <RepositoryDashboardPage /> },
          { path: "graph", element: <DependencyGraphPage /> },
          { path: "complexity", element: <ComplexityPage /> },
          { path: "dead-code", element: <DeadCodePage /> },
          { path: "architecture", element: <ArchitecturePage /> },
          { path: "impact", element: <ImpactAnalysisPage /> },
          { path: "chat", element: <AIAssistantPage /> },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
