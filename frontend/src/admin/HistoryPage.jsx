
import { useEffect, useState } from "react";
import { Clock3 } from "lucide-react";

import { apiRequest } from "../api";
import {
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  fieldStyle,
  Notice,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";

export default function HistoryPage({ token }) {
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest("/api/clients?limit=100", {}, token)
      .then((result) => {
        setClients(
          Array.isArray(result) ? result : result?.items || []
        );
      })
      .catch((err) => setError(err.message));
  }, [token]);

  async function loadHistory(id) {
    setClientId(id);
    setActivities([]);
    setError("");

    if (!id) return;

    setLoading(true);

    try {
      const result = await apiRequest(
        `/api/clients/${id}/activity?limit=100`,
        {},
        token
      );

      setActivities(
        Array.isArray(result) ? result : result?.items || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <ManagementHeader
        title="Access History"
        description="Review activity records for individual clients."
      />

      <section className="content-card" style={{ marginTop: "20px" }}>
        <div className="card-heading">
          <div>
            <h3>Client Activity</h3>
            <p>Select a client to view their activity.</p>
          </div>
          <Clock3 size={20} />
        </div>

        <select
          value={clientId}
          onChange={(e) => loadHistory(e.target.value)}
          style={{ ...fieldStyle, maxWidth: "400px" }}
        >
          <option value="">Select client</option>

          {clients.map((client) => (
            <option key={client.id} value={client.id}>
              {client.name} ({client.client_code || client.email})
            </option>
          ))}
        </select>

        <Notice message={error} error />

        <DataTable
          columns={["Activity", "Details", "IP Address", "Date"]}
          loading={loading}
          empty={
            clientId && activities.length === 0
              ? "No activity records found."
              : "Select a client to view activity."
          }
        >
          {activities.map((item, index) => (
            <tr key={item.id || index}>
              <TableCell>{item.activity}</TableCell>
              <TableCell>{item.details || "—"}</TableCell>
              <TableCell>{item.ip_address || "—"}</TableCell>
              <TableCell>
                {item.created_at
                  ? new Date(item.created_at).toLocaleString()
                  : "—"}
              </TableCell>
            </tr>
          ))}
        </DataTable>

        <p
          style={{
            color: "#64748b",
            fontSize: "12px",
            marginTop: "12px",
          }}
        >
          Activity history is currently available per client through
          the existing backend API.
        </p>
      </section>
    </>
  );
}
