
import { useState } from "react";
import { LockKeyhole } from "lucide-react";

import { apiRequest } from "../api";
import {
  FormField,
  Notice,
  PrimaryAction,
} from "../components/FormModal";
import ManagementHeader from "../components/ManagementHeader";

export default function SettingsPage({ token, onTokenChange }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function changePassword(e) {
    e.preventDefault();
    setMessage("");
    setError("");

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setError("New password must contain at least 8 characters.");
      return;
    }

    setBusy(true);

    try {
      const result = await apiRequest(
        "/api/auth/change-password",
        {
          method: "POST",
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        },
        token
      );

      if (result?.access_token) {
        onTokenChange(result.access_token);
      }

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Password changed successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ManagementHeader
        title="Settings"
        description="Manage your administrator account security."
      />

      <section
        className="content-card"
        style={{ marginTop: "20px", maxWidth: "600px" }}
      >
        <div className="card-heading">
          <div>
            <h3>Change Password</h3>
            <p>Update your account password securely.</p>
          </div>
          <LockKeyhole size={20} />
        </div>

        <form onSubmit={changePassword}>
          <FormField
            label="Current password"
            type="password"
            value={currentPassword}
            onChange={setCurrentPassword}
            required
          />

          <FormField
            label="New password"
            type="password"
            value={newPassword}
            onChange={setNewPassword}
            required
          />

          <FormField
            label="Confirm new password"
            type="password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            required
          />

          <Notice message={error} error />
          <Notice message={message} />

          <PrimaryAction type="submit" disabled={busy}>
            {busy ? "Updating..." : "Update Password"}
          </PrimaryAction>
        </form>
      </section>
    </>
  );
}
