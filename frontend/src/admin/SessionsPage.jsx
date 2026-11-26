
import { useEffect, useState } from "react";
import { RefreshCw, Square } from "lucide-react";

import { apiRequest } from "../api";
import {
  ActionButton,
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  Notice,
  SecondaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";
import StatusLabel from "../components/StatusLabel";

export default function SessionsPage({ token }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSessions() {
    setLoading(true);
    setError("");

    try {
      const result = await apiRequest(
        "/api/sessions?active_only=true",
        {},
        token
      );

      setSessions(
        Array.isArray(result) ? result : result?.items || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSessions();
  }, [token]);

  async function terminateSession(session) {
    if (
      !window.confirm(
        "Are you sure you want to terminate this session?"
      )
    ) {
      return;
    }

    try {
      await apiRequest(
        `/api/sessions/${encodeURIComponent(session.session_id)}/terminate`,
        {
          method: "POST",
          body: JSON.stringify({}),
        },
        token
      );

      await loadSessions();
    } catch (err) {
      window.alert(err.message);
    }
  }

  return (
    <>
      <ManagementHeader
        title="Sessions"
        description="Monitor and manage active remote application sessions."
        action={
          <SecondaryAction onClick={loadSessions}>
            <RefreshCw size={15} /> Refresh
          </SecondaryAction>
        }
      />

      <Notice message={error} error />

      <DataTable
        columns={[
          "Client",
          "Application",
          "Session ID",
          "Status",
          "Started",
          "Action",
        ]}
        loading={loading}
        empty={
          sessions.length === 0
            ? "No active sessions found."
            : ""
        }
      >
        {sessions.map((session) => (
          <tr key={session.id}>
            <TableCell>
              {session.client_code || session.client_id}
            </TableCell>

            <TableCell>
              {session.application_name || "—"}
            </TableCell>

            <TableCell>
              {session.session_id || "—"}
            </TableCell>

            <TableCell>
              <StatusLabel value={session.status} />
            </TableCell>

            <TableCell>
              {session.started_at
                ? new Date(session.started_at).toLocaleString()
                : "—"}
            </TableCell>

            <TableCell>
              <ActionButton
                title="Terminate session"
                danger
                onClick={() => terminateSession(session)}
              >
                <Square size={15} />
              </ActionButton>
            </TableCell>
          </tr>
        ))}
      </DataTable>
    </>
  );
}
