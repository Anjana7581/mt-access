
import { useCallback, useEffect, useState } from "react";
import "./App.css";

import { apiRequest } from "./api";

import AdminLogin from "./admin/AdminLogin";
import AdminDashboard from "./admin/AdminDashboard";

import ClientLogin from "./client/ClientLogin";
import ClientDashboard from "./client/ClientDashboard";
import RemoteApplication from "./client/RemoteApplication";

function getCurrentPath() {
  return window.location.pathname || "/admin/login";
}

export default function App() {
  const [path, setPath] = useState(getCurrentPath);

  const [token, setToken] = useState(
    () => sessionStorage.getItem("mt_access_token")
  );

  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(
    Boolean(sessionStorage.getItem("mt_access_token"))
  );
  const [authError, setAuthError] = useState("");

  // --------------------------------------------------
  // Navigation
  // --------------------------------------------------

  const navigate = useCallback((nextPath, replace = false) => {
    if (replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }

    setPath(nextPath);
  }, []);

  useEffect(() => {
    function handlePopState() {
      setPath(getCurrentPath());
    }

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  // --------------------------------------------------
  // Authentication
  // --------------------------------------------------

  const clearAuthentication = useCallback(() => {
    sessionStorage.removeItem("mt_access_token");
    setToken(null);
    setUser(null);
    setChecking(false);
  }, []);

  const loadUser = useCallback(async (accessToken) => {
    const currentUser = await apiRequest(
      "/api/auth/me",
      {},
      accessToken
    );

    if (!["admin", "client"].includes(currentUser.role)) {
      throw new Error("Your account does not have portal access.");
    }

    sessionStorage.setItem("mt_access_token", accessToken);

    setToken(accessToken);
    setUser(currentUser);
    setAuthError("");

    return currentUser;
  }, []);

  // Verify an existing session when the application loads
  useEffect(() => {
    let cancelled = false;

    async function verifySession() {
      if (!token) {
        setUser(null);
        setChecking(false);
        return;
      }

      setChecking(true);

      try {
        const currentUser = await apiRequest(
          "/api/auth/me",
          {},
          token
        );

        if (cancelled) return;

        if (!["admin", "client"].includes(currentUser.role)) {
          throw new Error("Invalid account role.");
        }

        setUser(currentUser);
      } catch {
        if (!cancelled) {
          clearAuthentication();
        }
      } finally {
        if (!cancelled) {
          setChecking(false);
        }
      }
    }

    verifySession();

    return () => {
      cancelled = true;
    };
  }, [token, clearAuthentication]);

  // --------------------------------------------------
  // Login
  // --------------------------------------------------

  async function handleLogin(accessToken, expectedRole) {
    setAuthError("");

    try {
      const currentUser = await loadUser(accessToken);

      if (currentUser.role !== expectedRole) {
        throw new Error(
          expectedRole === "admin"
            ? "This account is not an administrator account."
            : "This account is not a client account."
        );
      }

      navigate(
        expectedRole === "admin"
          ? "/admin"
          : "/client/dashboard",
        true
      );
    } catch (err) {
      sessionStorage.removeItem("mt_access_token");

      setToken(null);
      setUser(null);
      setAuthError(err.message || "Login failed.");

      throw err;
    }
  }

  // --------------------------------------------------
  // Logout
  // --------------------------------------------------

  async function handleLogout() {
    const previousRole = user?.role;

    try {
      if (token) {
        await apiRequest(
          "/api/auth/logout",
          { method: "POST" },
          token
        );
      }
    } catch {
      // Clear local authentication even if the API is unavailable.
    } finally {
      clearAuthentication();

      navigate(
        previousRole === "client"
          ? "/login"
          : "/admin/login",
        true
      );
    }
  }

  // --------------------------------------------------
  // Update token after password change
  // --------------------------------------------------

  function handleTokenChange(newToken) {
    if (!newToken) return;

    sessionStorage.setItem("mt_access_token", newToken);
    setToken(newToken);
  }

  // --------------------------------------------------
  // Route protection and redirects
  // --------------------------------------------------

  const remoteMatch = path.match(
    /^\/client\/remote\/([^/]+)$/
  );

  useEffect(() => {
    if (checking) return;

    // No authenticated user
    if (!token || !user) {
      if (
        path === "/" ||
        path === "/admin" ||
        path.startsWith("/admin/")
      ) {
        if (path !== "/admin/login") {
          navigate("/admin/login", true);
        }
      } else if (
        path !== "/login"
      ) {
        navigate("/login", true);
      }

      return;
    }

    // Administrator routes
    if (user.role === "admin") {
      if (path !== "/admin") {
        navigate("/admin", true);
      }

      return;
    }

    // Client routes
    if (user.role === "client") {
      const validClientRoute =
        path === "/client/dashboard" ||
        Boolean(remoteMatch);

      if (!validClientRoute) {
        navigate("/client/dashboard", true);
      }
    }
  }, [
    checking,
    token,
    user,
    path,
    navigate,
    remoteMatch?.[1],
  ]);

  // --------------------------------------------------
  // Loading screen
  // --------------------------------------------------

  if (checking) {
    return (
      <div className="loading-screen">
        Checking your session...
      </div>
    );
  }

  // --------------------------------------------------
  // Login pages
  // --------------------------------------------------

  if (!token || !user) {
    if (path === "/login") {
      return (
        <ClientLogin
          onLogin={(accessToken) =>
            handleLogin(accessToken, "client")
          }
          initialError={authError}
        />
      );
    }

    return (
      <AdminLogin
        onLogin={(accessToken) =>
          handleLogin(accessToken, "admin")
        }
        initialError={authError}
      />
    );
  }

  // --------------------------------------------------
  // Administrator portal
  // --------------------------------------------------

  if (user.role === "admin") {
    if (path === "/admin") {
      return (
        <AdminDashboard
          user={user}
          token={token}
          onLogout={handleLogout}
          onTokenChange={handleTokenChange}
        />
      );
    }

    return null;
  }

  // --------------------------------------------------
  // Client portal
  // --------------------------------------------------

  if (user.role === "client") {
    if (path === "/client/dashboard") {
      return (
        <ClientDashboard
          user={user}
          token={token}
          onLogout={handleLogout}
          onOpenRemote={(sessionId) => {
            navigate(
              `/client/remote/${encodeURIComponent(sessionId)}`
            );
          }}
        />
      );
    }

    if (remoteMatch) {
      return (
        <RemoteApplication
          token={token}
          sessionId={decodeURIComponent(remoteMatch[1])}
          onBack={() => navigate("/client/dashboard")}
        />
      );
    }

    return null;
  }

  return null;
}
