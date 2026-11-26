
import { useState } from "react";
import {
  ArrowRight,
  LockKeyhole,
  Monitor,
  ShieldCheck,
} from "lucide-react";

import { apiRequest } from "../api";

export default function ClientLogin({ onLogin, initialError = "" }) {
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
            Your trading platform.<br />
            <span>Accessed remotely.</span>
          </div>

          <p className="visual-description">
            Sign in to access your assigned MetaTrader application
            through the remote access platform.
          </p>

          <div className="visual-footer">
            <ShieldCheck size={17} />
            Secure client access
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

          <p className="eyebrow">CLIENT PORTAL</p>
          <h1>Welcome back</h1>

          <p className="login-subtitle">
            Sign in to access your assigned trading application.
          </p>

          <form onSubmit={submit}>
            <label htmlFor="client-email">Email address</label>

            <input
              id="client-email"
              type="email"
              placeholder="Enter your email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />

            <div className="password-label">
              <label htmlFor="client-password">Password</label>
            </div>

            <div className="password-input">
              <input
                id="client-password"
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
              {loading ? "Signing in..." : "Sign in to client portal"}
              {!loading && <ArrowRight size={18} />}
            </button>
          </form>

          <p className="login-security">
            <ShieldCheck size={15} /> Protected client access
          </p>
        </div>

        <p className="copyright">
          MT Access Management · Client Portal
        </p>
      </section>
    </main>
  );
}
