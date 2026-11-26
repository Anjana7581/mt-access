
import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, MonitorCog } from "lucide-react";

import { apiRequest } from "../api";
import {
  ActionButton,
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  FormField,
  FormModal,
  Notice,
  PrimaryAction,
  SecondaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";
import StatusLabel from "../components/StatusLabel";

export default function ApplicationsPage({ token }) {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  // RDP configuration state
  const [rdpModal, setRdpModal] = useState(false);
  const [rdpApplication, setRdpApplication] = useState(null);
  const [rdpBusy, setRdpBusy] = useState(false);
  const [rdpLoading, setRdpLoading] = useState(false);
  const [rdpNotice, setRdpNotice] = useState("");
  const [rdpConfigured, setRdpConfigured] = useState(false);

  const emptyForm = {
    application_name: "",
    application_type: "MT5",
    executable_path: "",
    working_directory: "",
    status: "active",
  };

  const emptyRdpForm = {
    hostname: "",
    port: 3389,
    username: "",
    password: "",
    remote_app_alias: "MT5",
  };

  const [form, setForm] = useState(emptyForm);
  const [rdpForm, setRdpForm] = useState(emptyRdpForm);

  async function loadApplications() {
    setLoading(true);
    setError("");

    try {
      const result = await apiRequest("/api/applications", {}, token);
      setApplications(
        Array.isArray(result) ? result : result?.items || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApplications();
  }, [token]);

  function openForm(app = null) {
    setEditing(app);
    setNotice("");

    setForm(
      app
        ? {
            application_name: app.application_name || "",
            application_type: app.application_type || "MT5",
            executable_path: app.executable_path || "",
            working_directory: app.working_directory || "",
            status: app.status || "active",
          }
        : emptyForm
    );

    setModal(true);
  }

  async function saveApplication(e) {
    e.preventDefault();
    setBusy(true);
    setNotice("");

    try {
      await apiRequest(
        editing
          ? `/api/applications/${editing.id}`
          : "/api/applications",
        {
          method: editing ? "PUT" : "POST",
          body: JSON.stringify(form),
        },
        token
      );

      setModal(false);
      await loadApplications();
    } catch (err) {
      setNotice(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteApplication(app) {
    if (!window.confirm(`Delete ${app.application_name}?`)) return;

    try {
      await apiRequest(
        `/api/applications/${app.id}`,
        { method: "DELETE" },
        token
      );

      await loadApplications();
    } catch (err) {
      window.alert(err.message);
    }
  }

  // Open RDP settings and load existing configuration
  async function openRdpSettings(app) {
    setRdpApplication(app);
    setRdpForm({
      ...emptyRdpForm,
      remote_app_alias: app.application_type || "MT5",
    });
    setRdpNotice("");
    setRdpConfigured(false);
    setRdpModal(true);
    setRdpLoading(true);

    try {
      const result = await apiRequest(
        `/api/applications/${app.id}/rdp-credentials`,
        {},
        token
      );

      setRdpForm({
        hostname: result.hostname || "",
        port: result.port || 3389,
        username: result.username || "",
        // Backend intentionally does not return the stored password.
        password: "",
        remote_app_alias: result.remote_app_alias || app.application_type || "MT5",
      });

      setRdpConfigured(true);
      setRdpNotice(
        "Existing RDP settings loaded. Enter the Windows password again when saving."
      );
    } catch (err) {
      if (
        err.message?.includes("404") ||
        err.message?.toLowerCase().includes("not configured")
      ) {
        setRdpNotice("No RDP credentials configured yet. Enter the details below.");
      } else {
        setRdpNotice(err.message);
      }
    } finally {
      setRdpLoading(false);
    }
  }

  async function saveRdpSettings(e) {
    e.preventDefault();

    if (!rdpApplication) return;

    setRdpBusy(true);
    setRdpNotice("");

    try {
      await apiRequest(
        `/api/applications/${rdpApplication.id}/rdp-credentials`,
        {
          method: "PUT",
          body: JSON.stringify({
            hostname: rdpForm.hostname.trim(),
            port: Number(rdpForm.port),
            username: rdpForm.username.trim(),
            password: rdpForm.password,
            remote_app_alias: rdpForm.remote_app_alias,
          }),
        },
        token
      );

      setRdpConfigured(true);
      setRdpNotice("RDP credentials saved successfully.");
      setRdpForm((previous) => ({
        ...previous,
        password: "",
      }));
    } catch (err) {
      setRdpNotice(err.message);
    } finally {
      setRdpBusy(false);
    }
  }

  return (
    <>
      <ManagementHeader
        title="Applications"
        description="Configure and manage your MetaTrader applications."
        action={
          <PrimaryAction onClick={() => openForm()}>
            <Plus size={16} /> Add Application
          </PrimaryAction>
        }
      />

      <Notice message={error} error />

      <DataTable
        columns={[
          "Application",
          "Type",
          "Executable Path",
          "Status",
          "Actions",
        ]}
        loading={loading}
        empty={
          applications.length === 0
            ? "No applications registered."
            : ""
        }
      >
        {applications.map((app) => (
          <tr key={app.id}>
            <TableCell>
              <strong>{app.application_name}</strong>
            </TableCell>

            <TableCell>{app.application_type}</TableCell>

            <TableCell>
              <span style={{ wordBreak: "break-all" }}>
                {app.executable_path}
              </span>
            </TableCell>

            <TableCell>
              <StatusLabel value={app.status} />
            </TableCell>

            <TableCell>
              <ActionButton
                title="Configure RDP"
                onClick={() => openRdpSettings(app)}
              >
                <MonitorCog size={15} />
              </ActionButton>

              <ActionButton
                title="Edit"
                onClick={() => openForm(app)}
              >
                <Pencil size={15} />
              </ActionButton>

              <ActionButton
                title="Delete"
                danger
                onClick={() => deleteApplication(app)}
              >
                <Trash2 size={15} />
              </ActionButton>
            </TableCell>
          </tr>
        ))}
      </DataTable>

      {/* Existing Application Form */}
      {modal && (
        <FormModal
          title={editing ? "Edit Application" : "Add Application"}
          onClose={() => setModal(false)}
        >
          <form onSubmit={saveApplication}>
            <FormField
              label="Application name"
              value={form.application_name}
              onChange={(v) =>
                setForm({ ...form, application_name: v })
              }
              required
            />

            <FormField
              label="Application type"
              value={form.application_type}
              onChange={(v) =>
                setForm({ ...form, application_type: v })
              }
              options={[
                { value: "MT4", label: "MetaTrader 4" },
                { value: "MT5", label: "MetaTrader 5" },
              ]}
              required
            />

            <FormField
              label="Executable path"
              value={form.executable_path}
              onChange={(v) =>
                setForm({ ...form, executable_path: v })
              }
              required
            />

            <FormField
              label="Working directory"
              value={form.working_directory}
              onChange={(v) =>
                setForm({ ...form, working_directory: v })
              }
            />

            <FormField
              label="Status"
              value={form.status}
              onChange={(v) =>
                setForm({ ...form, status: v })
              }
              options={[
                { value: "active", label: "Active" },
                { value: "inactive", label: "Inactive" },
              ]}
            />

            <Notice message={notice} error />

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "10px",
              }}
            >
              <SecondaryAction onClick={() => setModal(false)}>
                Cancel
              </SecondaryAction>

              <PrimaryAction type="submit" disabled={busy}>
                {busy ? "Saving..." : "Save Application"}
              </PrimaryAction>
            </div>
          </form>
        </FormModal>
      )}

      {/* Separate RDP Configuration Form */}
      {rdpModal && rdpApplication && (
        <FormModal
          title={`RDP Settings - ${rdpApplication.application_name}`}
          onClose={() => setRdpModal(false)}
        >
          {rdpLoading ? (
            <p>Loading RDP settings...</p>
          ) : (
            <form onSubmit={saveRdpSettings}>
              <p style={{ fontSize: "13px", color: "#64748b" }}>
                Configure the Windows machine credentials used by
                Apache Guacamole to access this application.
              </p>

              <FormField
                label="Hostname / IP address"
                value={rdpForm.hostname}
                onChange={(v) =>
                  setRdpForm({ ...rdpForm, hostname: v })
                }
                placeholder="192.168.1.100"
                required
              />

              <FormField
                label="RDP Port"
                value={String(rdpForm.port)}
                onChange={(v) =>
                  setRdpForm({ ...rdpForm, port: v })
                }
                required
              />

              <FormField
                label="Windows username"
                value={rdpForm.username}
                onChange={(v) =>
                  setRdpForm({ ...rdpForm, username: v })
                }
                placeholder="Administrator"
                required
              />

              <FormField
                label="Windows password"
                value={rdpForm.password}
                onChange={(v) =>
                  setRdpForm({ ...rdpForm, password: v })
                }
                type="password"
                placeholder={
                  rdpConfigured
                    ? "Enter password again to update credentials"
                    : "Enter Windows password"
                }
                required
              />

              <FormField
                label="RemoteApp alias"
                value={rdpForm.remote_app_alias}
                onChange={(v) =>
                  setRdpForm({
                    ...rdpForm,
                    remote_app_alias: v,
                  })
                }
                options={[
                  { value: "MT4", label: "MT4" },
                  { value: "MT5", label: "MT5" },
                ]}
                required
              />

              <Notice
                message={rdpNotice}
                error={
                  Boolean(rdpNotice) &&
                  !rdpNotice.includes("successfully") &&
                  !rdpNotice.includes("No RDP credentials") &&
                  !rdpNotice.includes("Existing RDP settings")
                }
              />

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                  marginTop: "16px",
                }}
              >
                <SecondaryAction
                  onClick={() => setRdpModal(false)}
                >
                  Close
                </SecondaryAction>

                <PrimaryAction
                  type="submit"
                  disabled={rdpBusy || rdpLoading}
                >
                  {rdpBusy ? "Saving..." : "Save RDP Settings"}
                </PrimaryAction>
              </div>
            </form>
          )}
        </FormModal>
      )}
    </>
  );
}
