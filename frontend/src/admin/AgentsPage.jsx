
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { apiRequest } from "../api";
import {
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  Notice,
  SecondaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";
import StatusLabel from "../components/StatusLabel";

export default function AgentsPage({ token }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAgents() {
    setLoading(true);
    setError("");

    try {
      const result = await apiRequest("/api/agents", {}, token);

      setAgents(
        Array.isArray(result) ? result : result?.items || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAgents();
  }, [token]);

  return (
    <>
      <ManagementHeader
        title="Agents"
        description="Monitor the registered Windows agents and their heartbeat status."
        action={
          <SecondaryAction onClick={loadAgents}>
            <RefreshCw size={15} /> Refresh
          </SecondaryAction>
        }
      />

      <Notice message={error} error />

      <DataTable
        columns={[
          "Agent Name",
          "Version",
          "Last Heartbeat",
          "Status",
        ]}
        loading={loading}
        empty={
          agents.length === 0
            ? "No agents registered."
            : ""
        }
      >
        {agents.map((agent) => (
          <tr key={agent.id}>
            <TableCell>
              <strong>{agent.name}</strong>
            </TableCell>

            <TableCell>{agent.version || "—"}</TableCell>

            <TableCell>
              {agent.last_seen
                ? new Date(agent.last_seen).toLocaleString()
                : "—"}
            </TableCell>

            <TableCell>
              <StatusLabel
                value={agent.online ? "Online" : "Offline"}
              />
            </TableCell>
          </tr>
        ))}
      </DataTable>
    </>
  );
}
