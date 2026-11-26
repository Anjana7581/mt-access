
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  LogOut,
  Monitor,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  UserRound,
  Wifi,
} from "lucide-react";

import { apiRequest } from "../api";
import AssignedApplications from "./AssignedApplications";
import {
  Notice,
  PrimaryAction,
  SecondaryAction,
} from "../components/FormModal";
import StatusLabel from "../components/StatusLabel";

export default function ClientDashboard({
  user,
  token,
  onLogout,
  onOpenRemote,
}) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  // Keep the client's remote-access state separate from the server app process.
  const disconnectStorageKey =
    `mt-access-remote-disconnected-${user?.id || user?.client_code || user?.email || "client"}`;

  const [remoteDisconnected, setRemoteDisconnected] = useState(
    () => localStorage.getItem(disconnectStorageKey) === "true"
  );

  const messageTimeoutRef = useRef(null);

  // Automatically clear success and error messages after 5 seconds.
  function showMessage(message, type = "success") {
    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
    }

    if (type === "error") {
      setError(message);
      setNotice("");
    } else {
      setNotice(message);
      setError("");
    }

    messageTimeoutRef.current = setTimeout(() => {
      setError("");
      setNotice("");
      messageTimeoutRef.current = null;
    }, 5000);
  }

  // Clear pending timeout when component unmounts.
  useEffect(() => {
    return () => {
      if (messageTimeoutRef.current) {
        clearTimeout(messageTimeoutRef.current);
      }
    };
  }, []);

  const loadSession = useCallback(
    async (silent = false) => {
      if (!silent) {
        setLoading(true);
      }

      try {
        const result = await apiRequest(
          "/api/sessions/status",
          {},
          token
        );

        setSession(result);
      } catch (err) {
        if (!silent) {
          showMessage(err.message, "error");
        }
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [token]
  );

  // Initial load and automatic session status refresh.
  useEffect(() => {
    loadSession();

    const interval = setInterval(() => {
      loadSession(true);
    }, 2000);

    return () => clearInterval(interval);
  }, [loadSession]);

  const status = String(session?.status || "none").toLowerCase();

  const applicationRunning =
    Boolean(session?.session_id) &&
    ["running", "active", "started"].includes(status);

  // A disconnected remote session must not be mistaken for a stopped app.
  const activeSession = applicationRunning && !remoteDisconnected;

  const sessionStarting =
    Boolean(session?.session_id) &&
    ["starting", "launching", "pending"].includes(status) &&
    !remoteDisconnected;

  async function launchSession() {
    setBusy(true);

    try {
      localStorage.removeItem(disconnectStorageKey);
      setRemoteDisconnected(false);

      const result = await apiRequest(
        "/api/sessions/launch",
        { method: "POST" },
        token
      );

      setSession(result);

      showMessage(
        result?.message || "Session launch request submitted."
      );

      if (result?.session_id) {
        setRefreshKey((value) => value + 1);

        const resultStatus = String(result.status || "").toLowerCase();

        if (["running", "active", "started"].includes(resultStatus)) {
          onOpenRemote(result.session_id);
        }
      }
    } catch (err) {
      showMessage(err.message, "error");
    } finally {
      setBusy(false);
      await loadSession(true);
    }
  }

  async function disconnectSession() {
    if (!session?.session_id) return;

    setBusy(true);

    try {
      await apiRequest(
        "/api/sessions/disconnect",
        { method: "POST" },
        token
      );

      // This changes only the client's dashboard state.
      // The backend endpoint must disconnect remote access without stopping MT4/MT5.
      localStorage.setItem(disconnectStorageKey, "true");
      setRemoteDisconnected(true);

      showMessage("Remote session disconnected successfully.");
    } catch (err) {
      showMessage(err.message, "error");
    } finally {
      setBusy(false);
      await loadSession(true);
    }
  }

  function openRemote() {
    if (session?.session_id) {
      onOpenRemote(session.session_id);
    }
  }

  return (
    <div className="dashboard-layout client-dashboard">
      <main className="dashboard-main" style={{ width: "100%" }}>
        <header className="topbar">
          <div className="topbar-left">
            <div className="client-brand">
              <div className="client-brand-icon">
                <Monitor size={19} />
              </div>
              <div>
                <strong>MT ACCESS</strong>
                <span>Client Portal</span>
              </div>
            </div>
          </div>

          <div className="topbar-right">
            <span className="admin-badge">
              <ShieldCheck size={14} />
              Client Account
            </span>

            <button
              className="logout-icon"
              title="Logout"
              onClick={onLogout}
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>

        <div className="page-content client-page-content">
          <div className="client-welcome">
            <div>
              <p className="eyebrow">CLIENT WORKSPACE</p>
              <h1>Welcome back, {user?.name || "Client"}</h1>
              <p className="page-subtitle">
                Access and manage your assigned trading workspace.
              </p>
            </div>

            <div className="client-welcome-profile">
              <div className="client-avatar">
                <UserRound size={22} />
              </div>
              <div>
                <strong>{user?.name || "Client"}</strong>
                <span>{user?.client_code || "Client Account"}</span>
              </div>
            </div>
          </div>

          <Notice message={error} error />
          <Notice message={notice} />

          <div className="client-section-heading">
            <div>
              <h2>Workspace Overview</h2>
              <p>Monitor your remote application and account.</p>
            </div>

            <button
              className="client-refresh-button"
              onClick={() => loadSession()}
              disabled={loading || busy}
            >
              <RefreshCw
                size={15}
                className={loading ? "client-spin" : ""}
              />
              Refresh
            </button>
          </div>

          <section className="client-session-card">
            <div className="client-session-top">
              <div className="client-session-icon">
                <Monitor size={25} />
              </div>

              <div className="client-session-heading">
                <span className="client-card-label">REMOTE WORKSPACE</span>
                <h3>Trading Application Session</h3>
                <p>
                  Launch and manage your assigned remote trading environment.
                </p>
              </div>

              <div className="client-session-status">
                <span>SESSION STATUS</span>
                {loading ? (
                  <span className="client-loading-status">
                    <RefreshCw size={13} className="client-spin" />
                    Checking...
                  </span>
                ) : (
                  <StatusLabel value={session?.status || "No session"} />
                )}
              </div>
            </div>

            <div className="client-session-divider" />

            <div className="client-session-details">
              <div className="client-session-detail">
                <span>Application</span>
                <strong>
                  {session?.application_name || "Assigned application"}
                </strong>
              </div>

              <div className="client-session-detail">
                <span>Session ID</span>
                <strong>
                  {session?.session_id || "Not started"}
                </strong>
              </div>

              <div className="client-session-detail">
                <span>Connection</span>
                <strong className="client-connection-value">
                  <Wifi size={14} />
                  {activeSession
                    ? "Remote session active"
                    : sessionStarting
                      ? "Starting..."
                      : remoteDisconnected
                        ? "Remote session disconnected"
                        : "Not connected"}
                </strong>
              </div>
            </div>

            <div className="client-session-actions">
              {activeSession ? (
                <>
                  <PrimaryAction onClick={openRemote} disabled={busy}>
                    <Monitor size={16} />
                    Open Workspace
                    <ArrowUpRight size={15} />
                  </PrimaryAction>

                  <SecondaryAction
                    onClick={disconnectSession}
                    disabled={busy}
                  >
                    {busy ? (
                      <RefreshCw size={15} className="client-spin" />
                    ) : (
                      <Square size={15} />
                    )}
                    {busy ? "Disconnecting..." : "Disconnect"}
                  </SecondaryAction>
                </>
              ) : sessionStarting ? (
                <PrimaryAction disabled>
                  <RefreshCw size={16} className="client-spin" />
                  Starting Trading Workspace...
                </PrimaryAction>
              ) : (
                <PrimaryAction
                  onClick={launchSession}
                  disabled={busy || loading}
                >
                  {busy ? (
                    <RefreshCw size={16} className="client-spin" />
                  ) : (
                    <Play size={16} />
                  )}
                  {busy
                    ? "Starting Workspace..."
                    : "Launch Trading Workspace"}
                </PrimaryAction>
              )}
            </div>
          </section>

          <div className="client-content-grid">
            <div className="client-assignment-column">
              <AssignedApplications
                token={token}
                refreshKey={refreshKey}
              />
            </div>

            <section className="content-card client-account-card">
              <div className="card-heading">
                <div>
                  <h3>Account Information</h3>
                  <p>Your registered account details.</p>
                </div>
                <div className="client-card-heading-icon">
                  <UserRound size={19} />
                </div>
              </div>

              <div className="client-account-details">
                <div className="client-account-item">
                  <span>Full Name</span>
                  <strong>{user?.name || "—"}</strong>
                </div>

                <div className="client-account-item">
                  <span>Email Address</span>
                  <strong>{user?.email || "—"}</strong>
                </div>

                <div className="client-account-item">
                  <span>Client Code</span>
                  <strong>{user?.client_code || "—"}</strong>
                </div>

                <div className="client-account-item">
                  <span>Account Status</span>
                  <strong className="client-account-status">
                    <CheckCircle2 size={14} />
                    {user?.status || "—"}
                  </strong>
                </div>
              </div>

              <div className="client-account-footer">
                <ShieldCheck size={15} />
                Your account is managed securely by your administrator.
              </div>
            </section>
          </div>

          <footer className="client-footer">
            <span>MT ACCESS Client Portal</span>
            <span>Secure Trading Workspace</span>
          </footer>
        </div>
      </main>

      <style>{`
        .client-dashboard {
          background: #f5f7fb;
          min-height: 100vh;
          color: #172033;
        }

        .client-dashboard .topbar {
          background: #ffffff;
          border-bottom: 1px solid #e9edf3;
          min-height: 70px;
          padding: 0 30px;
        }

        .client-brand {
          display: flex;
          align-items: center;
          gap: 11px;
        }

        .client-brand-icon {
          width: 39px;
          height: 39px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #edf3ff;
          color: #315fca;
          border-radius: 11px;
        }

        .client-brand strong,
        .client-brand span {
          display: block;
        }

        .client-brand strong {
          font-size: 14px;
          letter-spacing: .7px;
          color: #172033;
        }

        .client-brand span {
          font-size: 11px;
          color: #8490a3;
          margin-top: 3px;
        }

        .client-page-content {
          max-width: 1380px;
          margin: 0 auto;
          padding: 32px 34px;
        }

        .client-welcome {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 34px;
        }

        .client-welcome h1 {
          margin: 7px 0;
          font-size: 27px;
          font-weight: 700;
          letter-spacing: -.6px;
          color: #172033;
        }

        .client-welcome-profile {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 11px 16px;
          background: #ffffff;
          border: 1px solid #e9edf3;
          border-radius: 12px;
        }

        .client-avatar {
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          color: #315fca;
          background: #edf3ff;
        }

        .client-welcome-profile strong,
        .client-welcome-profile span {
          display: block;
        }

        .client-welcome-profile strong {
          font-size: 13px;
          color: #263248;
        }

        .client-welcome-profile span {
          margin-top: 4px;
          font-size: 11px;
          color: #8490a3;
        }

        .client-section-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 15px;
          margin-bottom: 15px;
        }

        .client-section-heading h2 {
          font-size: 17px;
          margin: 0 0 5px;
          color: #172033;
        }

        .client-section-heading p {
          font-size: 12px;
          margin: 0;
          color: #8792a5;
        }

        .client-refresh-button {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border: 1px solid #e0e6ef;
          border-radius: 8px;
          background: #ffffff;
          padding: 9px 13px;
          color: #526078;
          font-size: 12px;
          cursor: pointer;
        }

        .client-refresh-button:disabled {
          opacity: .6;
          cursor: not-allowed;
        }

        .client-session-card {
          padding: 24px;
          background: #ffffff;
          border: 1px solid #e8edf4;
          border-radius: 14px;
          margin-bottom: 24px;
          box-shadow: 0 3px 12px rgba(25, 42, 70, .035);
        }

        .client-session-top {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .client-session-icon {
          width: 52px;
          height: 52px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #315fca;
          background: #edf3ff;
          border-radius: 13px;
        }

        .client-session-heading {
          flex: 1;
          min-width: 0;
        }

        .client-card-label {
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 1px;
          color: #8794a8;
        }

        .client-session-heading h3 {
          font-size: 16px;
          margin: 5px 0;
          color: #202d43;
        }

        .client-session-heading p {
          font-size: 12px;
          color: #8490a3;
          margin: 0;
        }

        .client-session-status {
          min-width: 135px;
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 9px;
        }

        .client-session-status > span:first-child {
          font-size: 10px;
          letter-spacing: .7px;
          color: #8794a8;
          font-weight: 600;
        }

        .client-loading-status {
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 12px;
          color: #64748b;
        }

        .client-session-divider {
          height: 1px;
          background: #edf0f5;
          margin: 23px 0;
        }

        .client-session-details {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 18px;
          margin-bottom: 23px;
        }

        .client-session-detail {
          min-width: 0;
        }

        .client-session-detail span,
        .client-account-item span {
          display: block;
          margin-bottom: 7px;
          color: #8994a7;
          font-size: 11px;
        }

        .client-session-detail strong,
        .client-account-item strong {
          display: block;
          color: #344158;
          font-size: 13px;
          font-weight: 600;
          overflow-wrap: anywhere;
        }

        .client-connection-value,
        .client-account-status {
          display: flex !important;
          align-items: center;
          gap: 7px;
        }

        .client-connection-value {
          color: #64748b !important;
        }

        .client-session-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          align-items: center;
        }

        .client-content-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          align-items: stretch;
          gap: 20px;
        }

        .client-assignment-column {
          min-width: 0;
        }

        .client-content-grid .content-card {
          height: 100%;
          box-sizing: border-box;
        }

        .client-card-heading-icon {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #315fca;
          background: #edf3ff;
          border-radius: 10px;
        }

        .client-account-details {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 22px 18px;
          margin-top: 23px;
        }

        .client-account-status {
          color: #16845b !important;
          text-transform: capitalize;
        }

        .client-account-footer {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-top: 25px;
          padding-top: 15px;
          border-top: 1px solid #edf0f5;
          color: #8490a3;
          font-size: 11px;
          line-height: 1.6;
        }

        .client-account-footer svg {
          flex-shrink: 0;
          color: #6485c7;
        }

        .client-footer {
          display: flex;
          justify-content: space-between;
          gap: 15px;
          margin-top: 28px;
          padding-top: 17px;
          border-top: 1px solid #e7ebf2;
          color: #98a2b2;
          font-size: 11px;
        }

        .client-spin {
          animation: client-spin-animation 1s linear infinite;
        }

        @keyframes client-spin-animation {
          to {
            transform: rotate(360deg);
          }
        }

        @media (max-width: 850px) {
          .client-content-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 650px) {
          .client-dashboard .topbar {
            padding: 0 16px;
          }

          .client-page-content {
            padding: 24px 16px;
          }

          .client-welcome {
            align-items: flex-start;
            flex-direction: column;
          }

          .client-welcome h1 {
            font-size: 23px;
          }

          .client-welcome-profile {
            width: 100%;
            box-sizing: border-box;
          }

          .client-session-card {
            padding: 18px;
          }

          .client-session-top {
            flex-wrap: wrap;
          }

          .client-session-status {
            width: 100%;
            min-width: 0;
            align-items: flex-start;
            padding-left: 68px;
          }

          .client-session-details {
            grid-template-columns: 1fr;
            gap: 16px;
          }

          .client-account-details {
            grid-template-columns: 1fr;
            gap: 17px;
          }

          .client-session-actions {
            align-items: stretch;
            flex-direction: column;
          }

          .client-session-actions > button {
            width: 100%;
            justify-content: center;
          }

          .client-footer {
            flex-direction: column;
            gap: 6px;
          }

          .client-section-heading {
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
}
