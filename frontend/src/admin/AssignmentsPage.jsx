
import { useEffect, useState } from "react";
import { CircleUserRound, Trash2 } from "lucide-react";

import { apiRequest } from "../api";
import {
  ActionButton,
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  FormField,
  Notice,
  PrimaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";

export default function AssignmentsPage({ token }) {
  const [clients, setClients] = useState([]);
  const [applications, setApplications] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [clientId, setClientId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [clientResult, appResult, assignmentResult] =
        await Promise.all([
          apiRequest("/api/clients?limit=100", {}, token),
          apiRequest("/api/applications", {}, token),
          apiRequest("/api/assignments", {}, token),
        ]);

      setClients(
        Array.isArray(clientResult)
          ? clientResult
          : clientResult?.items || []
      );

      setApplications(
        Array.isArray(appResult)
          ? appResult
          : appResult?.items || []
      );

      setAssignments(
        Array.isArray(assignmentResult)
          ? assignmentResult
          : assignmentResult?.items || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [token]);

  async function assignApplication(e) {
    e.preventDefault();
    setBusy(true);
    setError("");

    try {
      await apiRequest(
        "/api/assignments",
        {
          method: "POST",
          body: JSON.stringify({
            client_id: Number(clientId),
            application_id: Number(applicationId),
          }),
        },
        token
      );

      setClientId("");
      setApplicationId("");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeAssignment(item) {
    const id = item.client_id || item.client?.id;

    if (
      !id ||
      !window.confirm("Remove this application assignment?")
    ) {
      return;
    }

    try {
      await apiRequest(
        `/api/assignments/${id}`,
        { method: "DELETE" },
        token
      );

      await loadData();
    } catch (err) {
      window.alert(err.message);
    }
  }

  return (
    <>
      <ManagementHeader
        title="Assignments"
        description="Control which trading application is assigned to each client."
      />

      <section className="content-card" style={{ marginTop: "20px" }}>
        <div className="card-heading">
          <div>
            <h3>Assign Application</h3>
            <p>Select a client and an available application.</p>
          </div>
          <CircleUserRound size={20} />
        </div>

        <form
          onSubmit={assignApplication}
          style={{
            display: "flex",
            gap: "15px",
            flexWrap: "wrap",
            alignItems: "end",
          }}
        >
          <div style={{ flex: "1 1 200px" }}>
            <FormField
              label="Client"
              value={clientId}
              onChange={setClientId}
              required
              options={[
                { value: "", label: "Select client" },
                ...clients
                  .filter((c) => c.status === "active")
                  .map((c) => ({
                    value: String(c.id),
                    label: `${c.name} (${c.client_code || c.email})`,
                  })),
              ]}
            />
          </div>

          <div style={{ flex: "1 1 200px" }}>
            <FormField
              label="Application"
              value={applicationId}
              onChange={setApplicationId}
              required
              options={[
                { value: "", label: "Select application" },
                ...applications
                  .filter((a) => a.status === "active")
                  .map((a) => ({
                    value: String(a.id),
                    label: `${a.application_name} (${a.application_type})`,
                  })),
              ]}
            />
          </div>

          <div style={{ marginBottom: "15px" }}>
            <PrimaryAction
              type="submit"
              disabled={busy || !clientId || !applicationId}
            >
              {busy ? "Assigning..." : "Assign Application"}
            </PrimaryAction>
          </div>
        </form>

        <Notice message={error} error />
      </section>

      <DataTable
        columns={[
          "Client",
          "Application",
          "Type",
          "Assigned Date",
          "Action",
        ]}
        loading={loading}
        empty={
          assignments.length === 0
            ? "No application assignments found."
            : ""
        }
      >
        {assignments.map((item) => (
          <tr key={item.id || item.client_id}>
            <TableCell>
              {item.client?.name ||
                item.client_name ||
                item.client_id}
            </TableCell>

            <TableCell>
              {item.application?.application_name ||
                item.application_name ||
                "—"}
            </TableCell>

            <TableCell>
              {item.application?.application_type ||
                item.application_type ||
                "—"}
            </TableCell>

            <TableCell>
              {item.assigned_at
                ? new Date(item.assigned_at).toLocaleDateString()
                : "—"}
            </TableCell>

            <TableCell>
              <ActionButton
                title="Remove assignment"
                danger
                onClick={() => removeAssignment(item)}
              >
                <Trash2 size={15} />
              </ActionButton>
            </TableCell>
          </tr>
        ))}
      </DataTable>
    </>
  );
}
