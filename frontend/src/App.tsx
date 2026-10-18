import { Navigate, Route, Routes } from "react-router-dom";
import { Protected, Shell } from "./components/layout";
import { L1_ROLES, L2_ROLES, L3_ROLES } from "./features/auth/paths";
import { L2Board, L3Board } from "./features/admin/Boards";
import { AdminHome, AdminIncidents, AnalyticsPage, AuditPage, CategoriesPage, DepartmentsPage, IntegrationsPage, RulesPage, UsersPage } from "./pages/admin";
import { ForgotPage, LoginPage, ResetPage, SignupPage } from "./pages/auth";
import { CitizenDashboard, IncidentDetailPage, MyReportsPage, NotificationsPage, OfficerHome, ProfilePage, ReportPage } from "./pages/citizen";
import { ExplorePage, HomePage, PrivacyPage, PublicIncidentPage, TermsPage } from "./pages/public";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/about" element={<Navigate to="/#about" replace />} />
        <Route path="/how-it-works" element={<Navigate to="/#how-it-works" replace />} />
        <Route path="/help" element={<Navigate to="/#help" replace />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/explore/:reference" element={<PublicIncidentPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPage />} />
        <Route path="/reset-password" element={<ResetPage />} />

        <Route element={<Protected />}>
          <Route path="/app" element={<CitizenDashboard />} />
          <Route path="/app/report" element={<ReportPage />} />
          <Route path="/app/reports" element={<MyReportsPage />} />
          <Route path="/app/reports/:id" element={<IncidentDetailPage />} />
          <Route path="/app/notifications" element={<NotificationsPage />} />
          <Route path="/app/profile" element={<ProfilePage />} />
        </Route>

        <Route element={<Protected roles={L1_ROLES} />}>
          <Route path="/officer" element={<OfficerHome />} />
          <Route path="/officer/incidents/:id" element={<IncidentDetailPage base="/officer" />} />
        </Route>

        <Route element={<Protected roles={L2_ROLES} />}>
          <Route path="/l2" element={<L2Board />} />
          <Route path="/l2/incidents/:id" element={<IncidentDetailPage base="/l2" />} />
        </Route>

        <Route element={<Protected roles={L3_ROLES} />}>
          <Route path="/l3" element={<L3Board />} />
          <Route path="/l3/incidents/:id" element={<IncidentDetailPage base="/l3" />} />
        </Route>

        <Route element={<Protected roles={L3_ROLES} />}>
          <Route path="/admin" element={<AdminHome />} />
          <Route path="/admin/incidents" element={<AdminIncidents />} />
          <Route path="/admin/incidents/:id" element={<IncidentDetailPage base="/admin/incidents" />} />
          <Route path="/admin/users" element={<UsersPage />} />
          <Route path="/admin/categories" element={<CategoriesPage />} />
          <Route path="/admin/departments" element={<DepartmentsPage />} />
          <Route path="/admin/rules" element={<RulesPage />} />
          <Route path="/admin/analytics" element={<AnalyticsPage />} />
          <Route path="/admin/audit" element={<AuditPage />} />
          <Route path="/admin/integrations" element={<IntegrationsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
