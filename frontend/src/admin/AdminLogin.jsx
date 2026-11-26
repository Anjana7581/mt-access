
import { useState } from "react";
import {
  ArrowRight,
  LockKeyhole,
  Monitor,
  ShieldCheck,
} from "lucide-react";

import { apiRequest } from "../api";

export default function AdminLogin({ onLogin, initialError = "" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initialError);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (!result?.access_token) {
        throw new Error("The server did not return an access token.");
      }

      await onLogin(result.access_token);
    } catch (err) {
      setError(err.message || "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-visual">
        <div className="visual-content">
          <div className="brand-mark">
            <Monitor size={25} />
          </div>

          <div className="brand-name">MT ACCESS</div>

          <div className="visual-heading">
            Manage remote access.<br />
            <span>From one place.</span>
          </div>

          <p className="visual-description">
            Manage clients, applications, assignments and remote sessions
            through your administration portal.
          </p>

          <div className="visual-footer">
            <ShieldCheck size={17} />
            Secure administrator access
          </div>
        </div>

        <div className="visual-decoration decoration-one" />
        <div className="visual-decoration decoration-two" />
      </section>

      <section className="login-panel">
        <div className="login-box">
          <div className="mobile-brand">
            <Monitor size={23} /> MT ACCESS
          </div>

          <div className="login-icon">
            <LockKeyhole size={23} />
          </div>

          <p className="eyebrow">ADMINISTRATOR PORTAL</p>
          <h1>Welcome back</h1>

          <p className="login-subtitle">
            Sign in to manage your remote access platform.
          </p>

          <form onSubmit={submit}>
            <label htmlFor="admin-email">Email address</label>

            <input
              id="admin-email"
              type="email"
              placeholder="Enter your email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />

            <div className="password-label">
              <label htmlFor="admin-password">Password</label>
            </div>

            <div className="password-input">
              <input
                id="admin-password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />

              <button
                type="button"
                className="show-password"
                onClick={() => setShowPassword((prev) => !prev)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>

            {error && (
              <div className="error-message">{error}</div>
            )}

            <button
              className="login-button"
              type="submit"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in to admin portal"}
              {!loading && <ArrowRight size={18} />}
            </button>
          </form>

          <p className="login-security">
            <ShieldCheck size={15} /> Protected administrator access
          </p>
        </div>

        <p className="copyright">
          MT Access Management · Admin Portal
        </p>
      </section>
    </main>
  );
}
