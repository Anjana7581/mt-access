
import { useEffect, useState } from "react";
import {
  Activity,
  AppWindow,
  ArrowRight,
  Bell,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleUserRound,
  Clock3,
  LayoutDashboard,
  LogOut,
  Menu,
  Monitor,
  Server,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

import { apiRequest } from "../api";

import ClientsPage from "./ClientsPage";
import ApplicationsPage from "./ApplicationsPage";
import AssignmentsPage from "./AssignmentsPage";
import AgentsPage from "./AgentsPage";
import SessionsPage from "./SessionsPage";
import HistoryPage from "./HistoryPage";
import SettingsPage from "./SettingsPage";

export default function AdminDashboard({
  user,
  token,
  onLogout,
  onTokenChange,
}) {
  const [activePage, setActivePage] = useState("Overview");
  const [mobileMenu, setMobileMenu] = useState(false);

  const [stats, setStats] = useState({
    clients: "—",
    applications: "—",
    sessions: "—",
    agents: "—",
  });

  const navigation = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Clients", icon: Users },
    { label: "Applications", icon: AppWindow },
    { label: "Assignments", icon: CircleUserRound },
    { label: "Agents", icon: Server },
    { label: "Sessions", icon: Activity },
    { label: "Access History", icon: Clock3 },
    { label: "Settings", icon: Settings },
  ];

  const selected = navigation.find(
    (item) => item.label === activePage
  );

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardStats() {
      try {
        const [clients, applications, sessions, agents] =
          await Promise.all([
            apiRequest("/api/clients?limit=100", {}, token),
            apiRequest("/api/applications", {}, token),
            apiRequest("/api/sessions?active_only=true", {}, token),
            apiRequest("/api/agents", {}, token),
          ]);

        if (cancelled) return;

        const clientList = Array.isArray(clients)
          ? clients
          : clients?.items || [];

        const appList = Array.isArray(applications)
          ? applications
          : applications?.items || [];

        const sessionList = Array.isArray(sessions)
          ? sessions
          : sessions?.items || [];

        const agentList = Array.isArray(agents)
          ? agents
          : agents?.items || [];

        setStats({
          clients: clientList.length,
          applications: appList.length,
          sessions: sessionList.length,
          agents: agentList.filter((agent) => agent.online).length,
        });
      } catch (err) {
        console.error("Dashboard statistics error:", err);
      }
    }

    loadDashboardStats();

    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="dashboard-layout">
      {mobileMenu && (
        <div
          className="mobile-overlay"
          onClick={() => setMobileMenu(false)}
        />
      )}

      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-mark small">
            <Monitor size={21} />
          </div>

          <div>
            <strong>MT ACCESS</strong>
            <small>Management Platform</small>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileMenu(false)}
          >
            <X />
          </button>
        </div>

        <div className="nav-caption">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.label}
                className={`nav-item ${
                  activePage === item.label ? "active" : ""
                }`}
                onClick={() => {
                  setActivePage(item.label);
                  setMobileMenu(false);
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>

                {item.label === "Overview" && (
                  <span className="nav-indicator" />
                )}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span /> Backend connection configured
          </div>

          <div className="sidebar-user">
            <div className="avatar">
              {(user.email || "A")[0].toUpperCase()}
            </div>

            <div className="sidebar-user-info">
              <strong>{user.email}</strong>
              <small>Administrator</small>
            </div>

            <button
              className="logout-icon"
              title="Logout"
              onClick={onLogout}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu"
              onClick={() => setMobileMenu(true)}
            >
              <Menu />
            </button>

            <div>
              <span className="breadcrumb">Workspace /</span>{" "}
              {activePage}
            </div>
          </div>

          <div className="topbar-right">
            <span className="admin-badge">
              <ShieldCheck size={14} /> Admin
            </span>

            <button
              className="notification-button"
              title="Notifications"
            >
              <Bell size={19} />
            </button>

            <div className="topbar-avatar">
              {(user.email || "A")[0].toUpperCase()}
            </div>
          </div>
        </header>

        <div className="page-content">
          {activePage === "Overview" ? (
            <>
              <div className="welcome-row">
                <div>
                  <p className="eyebrow">ADMINISTRATION</p>
                </div>
              </div>

              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-top">
                    <span>Clients</span>
                    <Users />
                  </div>
                  <strong>{stats.clients}</strong>
                  <small>Client records</small>
                </div>

                <div className="stat-card">
                  <div className="stat-top">
                    <span>Applications</span>
                    <AppWindow />
                  </div>
                  <strong>{stats.applications}</strong>
                  <small>Registered MT4 / MT5 apps</small>
                </div>

                <div className="stat-card">
                  <div className="stat-top">
                    <span>Active sessions</span>
                    <Activity />
                  </div>
                  <strong>{stats.sessions}</strong>
                  <small>Remote session activity</small>
                </div>

                <div className="stat-card">
                  <div className="stat-top">
                    <span>Agents online</span>
                    <Server />
                  </div>
                  <strong>{stats.agents}</strong>
                  <small>Online registered agents</small>
                </div>
              </div>

              <div className="content-grid">
                <section className="content-card">
                  <div className="card-heading">
                    <div>
                      <h3>Quick management</h3>
                      <p>Navigate to platform management areas.</p>
                    </div>
                    <ChartNoAxesCombined size={20} />
                  </div>

                  <div className="quick-links">
                    {navigation.slice(1, 6).map((item) => {
                      const Icon = item.icon;

                      return (
                        <button
                          key={item.label}
                          onClick={() => setActivePage(item.label)}
                        >
                          <Icon size={19} />
                          <span>{item.label}</span>
                          <ArrowRight size={16} />
                        </button>
                      );
                    })}
                  </div>
                </section>

                <section className="content-card account-card">
                  <div className="card-heading">
                    <div>
                      <h3>Account information</h3>
                      <p>Current administrator</p>
                    </div>
                    <CircleUserRound size={20} />
                  </div>

                  <div className="account-detail">
                    <span>Email</span>
                    <strong>{user.email}</strong>
                  </div>

                  <div className="account-detail">
                    <span>Role</span>
                    <strong>Administrator</strong>
                  </div>

                  <div className="account-detail">
                    <span>Authentication</span>
                    <strong className="auth-ok">
                      <CheckCircle2 size={15} /> Verified
                    </strong>
                  </div>
                </section>
              </div>

              <p className="data-note">
                Dashboard statistics are loaded from the management APIs.
              </p>
            </>
          ) : activePage === "Clients" ? (
            <ClientsPage token={token} />
          ) : activePage === "Applications" ? (
            <ApplicationsPage token={token} />
          ) : activePage === "Assignments" ? (
            <AssignmentsPage token={token} />
          ) : activePage === "Agents" ? (
            <AgentsPage token={token} />
          ) : activePage === "Sessions" ? (
            <SessionsPage token={token} />
          ) : activePage === "Access History" ? (
            <HistoryPage token={token} />
          ) : activePage === "Settings" ? (
            <SettingsPage
              token={token}
              onTokenChange={onTokenChange}
            />
          ) : (
            <section className="coming-soon">
              <div className="coming-icon">
                {selected && <selected.icon size={28} />}
              </div>

              <h1>{activePage}</h1>
              <p>This section is not available.</p>

              <button
                className="back-button"
                onClick={() => setActivePage("Overview")}
              >
                Back to overview
              </button>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
