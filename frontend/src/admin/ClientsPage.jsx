
import { useEffect, useState } from "react";
import {
  Activity,
  Eye,
  EyeOff,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Copy,
  Check,
} from "lucide-react";

import { apiRequest } from "../api";
import {
  ActionButton,
  DataTable,
  TableCell,
} from "../components/DataTable";
import {
  fieldStyle,
  FormField,
  FormModal,
  Notice,
  PrimaryAction,
  SecondaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";
import StatusLabel from "../components/StatusLabel";

export default function ClientsPage({ token }) {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [generatedPassword, setGeneratedPassword] = useState("");
  const [showInitialPassword, setShowInitialPassword] = useState(false);

  // Password reset modal states
  const [resetClient, setResetClient] = useState(null);
  const [resetBusy, setResetBusy] = useState(false);
  const [resetNotice, setResetNotice] = useState("");
  const [resetGeneratedPassword, setResetGeneratedPassword] = useState("");
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [passwordCopied, setPasswordCopied] = useState(false);

  const [form, setForm] = useState({
    name: "",
    email: "",
    client_code: "",
    password: "",
  });

  async function loadClients() {
    setLoading(true);
    setError("");

    try {
      const result = await apiRequest("/api/clients?limit=100", {}, token);
      setClients(Array.isArray(result) ? result : result?.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
  }, [token]);

  function openCreate() {
    setEditing(null);
    setForm({ name: "", email: "", client_code: "", password: "" });
    setNotice("");
    setGeneratedPassword("");
    setModal(true);
    setShowInitialPassword(false);
  }

  function openEdit(client) {
    setEditing(client);
    setForm({
      name: client.name || "",
      email: client.email || "",
      client_code: "",
      password: "",
    });
    setNotice("");
    setGeneratedPassword("");
    setModal(true);
    setShowInitialPassword(false);
  }

  async function saveClient(e) {
    e.preventDefault();
    setBusy(true);
    setNotice("");
    setGeneratedPassword("");

    try {
      if (editing) {
        await apiRequest(
          `/api/clients/${editing.id}`,
          {
            method: "PUT",
            body: JSON.stringify({
              name: form.name,
              email: form.email,
            }),
          },
          token
        );

        setNotice("Client updated successfully.");
        setModal(false);
      } else {
        const payload = {
          name: form.name,
          email: form.email,
        };

        if (form.client_code.trim()) {
          payload.client_code = form.client_code.trim();
        }

        if (form.password.trim()) {
          payload.password = form.password;
        }

        const result = await apiRequest(
          "/api/clients",
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
          token
        );

        setGeneratedPassword(result?.initial_password || "");
        setNotice(
          "Client created successfully. Save the initial password if one was generated."
        );
      }

      await loadClients();
    } catch (err) {
      setNotice(err.message);
    } finally {
      setBusy(false);
    }
  }

  function openResetPassword(client) {
    setResetClient(client);
    setResetNotice("");
    setResetGeneratedPassword("");
    setShowResetPassword(false);
    setPasswordCopied(false);
  }

  function closeResetModal() {
    setResetClient(null);
    setResetNotice("");
    setResetGeneratedPassword("");
    setShowResetPassword(false);
    setPasswordCopied(false);
  }

  async function confirmResetPassword() {
    if (!resetClient) return;

    setResetBusy(true);
    setResetNotice("");

    try {
      const result = await apiRequest(
        `/api/clients/${resetClient.id}/reset-password`,
        {
          method: "POST",
          body: JSON.stringify({}),
        },
        token
      );

      if (result?.generated_password) {
        setResetGeneratedPassword(result.generated_password);
        setResetNotice("Password reset successfully.");
      } else {
        setResetNotice("Password reset successfully.");
      }

      await loadClients();
    } catch (err) {
      setResetNotice(err.message);
    } finally {
      setResetBusy(false);
    }
  }

  async function copyResetPassword() {
    try {
      await navigator.clipboard.writeText(resetGeneratedPassword);
      setPasswordCopied(true);
    } catch {
      setResetNotice("Unable to copy password. Please copy it manually.");
    }
  }

  async function toggleStatus(client) {
    const nextStatus =
      client.status === "active" ? "inactive" : "active";

    if (
      !window.confirm(
        `${nextStatus === "active" ? "Activate" : "Deactivate"} ${client.name}?`
      )
    ) {
      return;
    }

    try {
      await apiRequest(
        `/api/clients/${client.id}`,
        {
          method: "PUT",
          body: JSON.stringify({ status: nextStatus }),
        },
        token
      );

      await loadClients();
    } catch (err) {
      window.alert(err.message);
    }
  }

  async function deleteClient(client) {
    if (!window.confirm(`Delete or deactivate ${client.name}?`)) return;

    try {
      await apiRequest(
        `/api/clients/${client.id}`,
        { method: "DELETE" },
        token
      );

      await loadClients();
    } catch (err) {
      window.alert(err.message);
    }
  }

  const filtered = clients.filter((client) =>
    `${client.name} ${client.email} ${client.client_code || ""}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <>
      <ManagementHeader
        title="Client Management"
        description="Create and manage client accounts and access."
        action={
          <PrimaryAction onClick={openCreate}>
            <Plus size={16} /> Add Client
          </PrimaryAction>
        }
      />

      <Notice message={error} error />

      <section className="content-card" style={{ marginTop: "20px" }}>
        <div className="card-heading">
          <div>
            <h3>All Clients</h3>
            <p>{clients.length} registered client accounts</p>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <Search size={17} />
            <input
              placeholder="Search clients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ ...fieldStyle, width: "190px", margin: 0 }}
            />
            <SecondaryAction onClick={loadClients}>
              <RefreshCw size={15} />
            </SecondaryAction>
          </div>
        </div>

        <DataTable
          columns={["Client", "Client Code", "Application", "Status", "Actions"]}
          loading={loading}
          empty={filtered.length === 0 ? "No clients found." : ""}
        >
          {filtered.map((client) => (
            <tr key={client.id}>
              <TableCell>
                <strong>{client.name}</strong>
                <div style={{ color: "#64748b", marginTop: "4px" }}>
                  {client.email}
                </div>
              </TableCell>

              <TableCell>{client.client_code || "—"}</TableCell>

              <TableCell>
                {client.assignment?.application?.application_name ||
                  client.assignment?.application_name ||
                  "Not assigned"}
              </TableCell>

              <TableCell>
                <StatusLabel value={client.status} />
              </TableCell>

              <TableCell>
                <ActionButton
                  title="Edit client"
                  onClick={() => openEdit(client)}
                >
                  <Pencil size={15} />
                </ActionButton>

                <ActionButton
                  title="Reset password"
                  onClick={() => openResetPassword(client)}
                >
                  <KeyRound size={15} />
                </ActionButton>

                <ActionButton
                  title="Change status"
                  onClick={() => toggleStatus(client)}
                >
                  <Activity size={15} />
                </ActionButton>

                <ActionButton
                  title="Delete client"
                  danger
                  onClick={() => deleteClient(client)}
                >
                  <Trash2 size={15} />
                </ActionButton>
              </TableCell>
            </tr>
          ))}
        </DataTable>
      </section>

      {/* Create / Edit Client Modal */}
      {modal && (
        <FormModal
          title={editing ? "Edit Client" : "Create Client"}
          onClose={() => setModal(false)}
        >
          <form onSubmit={saveClient}>
            <FormField
              label="Full name"
              value={form.name}
              onChange={(v) => setForm({ ...form, name: v })}
              required
            />

            <FormField
              label="Email address"
              type="email"
              value={form.email}
              onChange={(v) => setForm({ ...form, email: v })}
              required
            />

            {!editing && (
              <>
                <FormField
                  label="Client code (optional)"
                  value={form.client_code}
                  onChange={(v) => setForm({ ...form, client_code: v })}
                />

                <div>
                  <label style={{ fontSize: "13px", fontWeight: 600 }}>
                    Initial password (optional)
                  </label>

                  <div style={{ position: "relative" }}>
                    <input
                      style={{
                        ...fieldStyle,
                        paddingRight: "42px",
                        boxSizing: "border-box",
                      }}
                      type={showInitialPassword ? "text" : "password"}
                      value={form.password}
                      onChange={(e) =>
                        setForm({ ...form, password: e.target.value })
                      }
                      placeholder="Enter initial password"
                    />

                    <button
                      type="button"
                      onClick={() =>
                        setShowInitialPassword((prev) => !prev)
                      }
                      title={
                        showInitialPassword
                          ? "Hide password"
                          : "Show password"
                      }
                      aria-label={
                        showInitialPassword
                          ? "Hide password"
                          : "Show password"
                      }
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "12px",
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        color: "#64748b",
                        padding: "2px",
                      }}
                    >
                      {showInitialPassword ? (
                        <EyeOff size={17} />
                      ) : (
                        <Eye size={17} />
                      )}
                    </button>
                  </div>
                </div>
              </>
            )}

            <Notice
              message={notice}
              error={
                !generatedPassword &&
                notice.includes("successfully") === false
              }
            />

            {generatedPassword && (
              <div
                style={{
                  padding: "12px",
                  background: "#edf8f0",
                  borderRadius: "8px",
                  marginBottom: "15px",
                }}
              >
                <strong>Generated initial password</strong>
                <p style={{ wordBreak: "break-all" }}>
                  {generatedPassword}
                </p>
                <SecondaryAction
                  onClick={() =>
                    navigator.clipboard.writeText(generatedPassword)
                  }
                >
                  <Copy size={15} /> Copy password
                </SecondaryAction>
              </div>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "10px",
              }}
            >
              <SecondaryAction onClick={() => setModal(false)}>
                Close
              </SecondaryAction>

              {!generatedPassword && (
                <PrimaryAction type="submit" disabled={busy}>
                  {busy
                    ? "Saving..."
                    : editing
                      ? "Save Changes"
                      : "Create Client"}
                </PrimaryAction>
              )}
            </div>
          </form>
        </FormModal>
      )}

      {/* Reset Password Confirmation / Result Modal */}
      {resetClient && (
        <FormModal
          title={
            resetGeneratedPassword
              ? "Password Reset Successful"
              : "Reset Client Password"
          }
          onClose={closeResetModal}
        >
          {!resetGeneratedPassword ? (
            <>
              <div style={{ marginBottom: "20px" }}>
                <p style={{ fontSize: "14px", color: "#475569" }}>
                  Are you sure you want to reset the password for:
                </p>

                <div
                  style={{
                    padding: "14px",
                    background: "#f8fafc",
                    borderRadius: "8px",
                    marginTop: "12px",
                  }}
                >
                  <strong>{resetClient.name}</strong>
                  <div
                    style={{
                      color: "#64748b",
                      fontSize: "13px",
                      marginTop: "4px",
                    }}
                  >
                    {resetClient.email}
                  </div>
                </div>

                <p
                  style={{
                    fontSize: "13px",
                    color: "#64748b",
                    marginTop: "14px",
                  }}
                >
                  A new password will be generated. Make sure to copy and
                  securely share it with the client.
                </p>
              </div>

              <Notice message={resetNotice} error={!!resetNotice} />

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <SecondaryAction
                  onClick={closeResetModal}
                  disabled={resetBusy}
                >
                  Cancel
                </SecondaryAction>

                <PrimaryAction
                  onClick={confirmResetPassword}
                  disabled={resetBusy}
                >
                  <KeyRound size={15} />
                  {resetBusy ? "Resetting..." : "Confirm Reset"}
                </PrimaryAction>
              </div>
            </>
          ) : (
            <>
              <div style={{ marginBottom: "16px" }}>
                <p style={{ color: "#475569", fontSize: "14px" }}>
                  The password for <strong>{resetClient.name}</strong> has
                  been successfully reset.
                </p>

                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "7px",
                  }}
                >
                  New generated password
                </label>

                <div style={{ position: "relative" }}>
                  <input
                    readOnly
                    value={resetGeneratedPassword}
                    type={showResetPassword ? "text" : "password"}
                    style={{
                      ...fieldStyle,
                      paddingRight: "76px",
                      boxSizing: "border-box",
                    }}
                  />

                  <div
                    style={{
                      position: "absolute",
                      right: "10px",
                      top: "10px",
                      display: "flex",
                      gap: "10px",
                    }}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setShowResetPassword((prev) => !prev)
                      }
                      title={showResetPassword ? "Hide password" : "Show password"}
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        color: "#64748b",
                        padding: "2px",
                      }}
                    >
                      {showResetPassword ? (
                        <EyeOff size={17} />
                      ) : (
                        <Eye size={17} />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <Notice
                message={passwordCopied ? "Password copied successfully." : resetNotice}
                error={false}
              />

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <SecondaryAction onClick={closeResetModal}>
                  Close
                </SecondaryAction>

                <PrimaryAction onClick={copyResetPassword}>
                  {passwordCopied ? (
                    <Check size={15} />
                  ) : (
                    <Copy size={15} />
                  )}
                  {passwordCopied ? "Copied" : "Copy Password"}
                </PrimaryAction>
              </div>
            </>
          )}
        </FormModal>
      )}
    </>
  );
}
