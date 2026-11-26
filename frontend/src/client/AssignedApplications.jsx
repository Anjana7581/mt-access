
import { useEffect, useState } from "react";
import {
  AppWindow,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

import { apiRequest } from "../api";
import {
  Notice,
  SecondaryAction,
} from "../components/FormModal";
import StatusLabel from "../components/StatusLabel";

export default function AssignedApplications({ token, refreshKey = 0 }) {
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAssignment() {
    setLoading(true);
    setError("");

    try {
      const user = await apiRequest("/api/auth/me", {}, token);

      const result = await apiRequest(
        `/api/assignments/${user.id}`,
        {},
        token
      );

      setAssignment(result);
    } catch (err) {
      setAssignment(null);
      setError(
        err.message || "Unable to load your assigned application."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAssignment();
  }, [token, refreshKey]);

  const application = assignment?.application;

  const applicationType =
    application?.application_type === "MT5"
      ? "MetaTrader 5"
      : application?.application_type === "MT4"
        ? "MetaTrader 4"
        : application?.application_type;

  return (
    <section className="content-card client-assigned-card">
      <div className="card-heading">
        <div>
          <h3>Assigned Application</h3>
          <p>Your administrator-assigned trading software.</p>
        </div>

        <div className="client-card-heading-icon">
          <AppWindow size={19} />
        </div>
      </div>

      <div className="client-assigned-refresh">
        <span>APPLICATION DETAILS</span>

        <SecondaryAction onClick={loadAssignment} disabled={loading}>
          <RefreshCw
            size={14}
            className={loading ? "client-spin" : ""}
          />
          Refresh
        </SecondaryAction>
      </div>

      {loading ? (
        <div className="client-assigned-loading">
          <RefreshCw size={20} className="client-spin" />
          <span>Loading assigned application...</span>
        </div>
      ) : error ? (
        <Notice message={error} error />
      ) : application ? (
        <div className="client-assigned-details">
          <div className="client-assigned-main">
            <div className="client-assigned-app-icon">
              <AppWindow size={24} />
            </div>

            <div className="client-assigned-app-name">
              <h3>{application.application_name}</h3>
              <span>{applicationType}</span>
            </div>
          </div>

          <div className="client-assigned-status">
            <span>APPLICATION STATUS</span>
            <StatusLabel value={application.status} />
          </div>

          <div className="client-assigned-note">
            <ShieldCheck size={15} />
            <span>
              Application configuration and access are managed by your
              administrator.
            </span>
          </div>
        </div>
      ) : (
        <Notice
          message="No application is currently assigned to your account. Please contact your administrator."
          error
        />
      )}

      <style>{`
        .client-assigned-card {
          min-width: 0;
        }

        .client-assigned-refresh {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          margin: 20px 0 15px;
        }

        .client-assigned-refresh > span,
        .client-assigned-status > span {
          color: #8994a7;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .7px;
        }

        .client-assigned-loading {
          min-height: 130px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 12px;
          color: #8490a3;
          font-size: 12px;
        }

        .client-assigned-details {
          padding: 17px;
          border: 1px solid #e9edf3;
          border-radius: 11px;
          background: #fbfcfe;
        }

        .client-assigned-main {
          display: flex;
          align-items: center;
          gap: 13px;
        }

        .client-assigned-app-icon {
          width: 45px;
          height: 45px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #315fca;
          background: #edf3ff;
          border-radius: 11px;
        }

        .client-assigned-app-name {
          min-width: 0;
        }

        .client-assigned-app-name h3 {
          margin: 0 0 5px;
          font-size: 14px;
          color: #263248;
          overflow-wrap: anywhere;
        }

        .client-assigned-app-name span {
          font-size: 12px;
          color: #8490a3;
        }

        .client-assigned-status {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          margin-top: 19px;
          padding-top: 15px;
          border-top: 1px solid #e9edf3;
        }

        .client-assigned-note {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-top: 17px;
          color: #8490a3;
          font-size: 11px;
          line-height: 1.6;
        }

        .client-assigned-note svg {
          flex-shrink: 0;
          color: #6485c7;
        }

        @media (max-width: 500px) {
          .client-assigned-refresh {
            align-items: flex-start;
          }
        }
      `}</style>
    </section>
  );
}
