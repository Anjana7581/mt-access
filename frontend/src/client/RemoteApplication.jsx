
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Monitor,
  RefreshCw,
  ShieldCheck,
  Unplug,
  X,
} from "lucide-react";

import Guacamole from "@pelotech/guacamole-common-js";

import { apiRequest } from "../api";
import {
  Notice,
  SecondaryAction,
  PrimaryAction,
} from "../components/FormModal";

const GUACAMOLE_URL = (
  import.meta.env.VITE_GUACAMOLE_URL ||
  "http://localhost:5173/guacamole"
).replace(/\/+$/, "");

function getWebSocketUrl() {
  const url = new URL(GUACAMOLE_URL);

  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";

  url.pathname = `${url.pathname}/websocket-tunnel`.replace(
    /\/+/g,
    "/"
  );

  return url.toString();
}

export default function RemoteApplication({
  token,
  sessionId,
  onBack,
}) {
  const displayRef = useRef(null);
  const clientRef = useRef(null);
  const keyboardRef = useRef(null);
  const disconnectingRef = useRef(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Connecting");
  const [showDisconnect, setShowDisconnect] = useState(false);

  const cleanupViewer = useCallback(() => {
    disconnectingRef.current = true;

    try {
      if (keyboardRef.current) {
        keyboardRef.current.reset();
        keyboardRef.current = null;
      }

      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
    } catch (err) {
      console.error("Viewer cleanup error:", err);
    }

    if (displayRef.current) {
      displayRef.current.replaceChildren();
    }
  }, []);

  const connectViewer = useCallback(async () => {
    console.log("[MT ACCESS] Starting viewer connection");

    cleanupViewer();

    disconnectingRef.current = false;

    setLoading(true);
    setError("");
    setStatus("Connecting");

    try {
      if (!token) {
        throw new Error("Your login session has expired.");
      }

      console.log("[MT ACCESS] Requesting Guacamole token");

      const auth = await apiRequest(
        "/api/viewer/token",
        { method: "POST" },
        token
      );

      console.log("[MT ACCESS] Token response received", {
        hasAuthToken: Boolean(auth?.authToken),
        dataSource: auth?.dataSource,
      });

      if (!auth?.authToken) {
        throw new Error(
          "Guacamole authentication token was not returned."
        );
      }

      const dataSource =
        auth.dataSource || auth.availableDataSources?.[0];

      if (!dataSource) {
        throw new Error(
          "Guacamole authentication data source is missing."
        );
      }

      console.log("[MT ACCESS] Retrieving Guacamole connections");

      const connectionUrl = new URL(
        `${GUACAMOLE_URL}/api/session/data/${encodeURIComponent(
          dataSource
        )}/connections`
      );

      connectionUrl.searchParams.set("token", auth.authToken);

      const response = await fetch(connectionUrl.toString());

      if (!response.ok) {
        throw new Error(
          `Unable to retrieve Guacamole connections (${response.status}).`
        );
      }

      const connections = await response.json();

      console.log(
        "[MT ACCESS] Guacamole connections received",
        Object.keys(connections || {})
      );

      const entries = Object.entries(connections || {});

      if (entries.length !== 1) {
        throw new Error(
          "Expected exactly one authorized remote application connection."
        );
      }

      const [connectionId] = entries[0];

      if (!displayRef.current) {
        throw new Error("Remote desktop display is unavailable.");
      }

      const websocketUrl = getWebSocketUrl();

      console.log("[MT ACCESS] Creating WebSocket tunnel", {
        websocketPath: new URL(websocketUrl).pathname,
      });

      const tunnel = new Guacamole.WebSocketTunnel(websocketUrl);

      const client = new Guacamole.Client(tunnel);

      clientRef.current = client;

      const displayElement = client.getDisplay().getElement();

      displayElement.style.width = "100%";
      displayElement.style.height = "100%";

      displayRef.current.replaceChildren(displayElement);

      client.onerror = (status) => {
        console.error(
          "[MT ACCESS] Guacamole client error:",
          status
        );

        if (!disconnectingRef.current) {
          setError(
            status?.message ||
              "Remote desktop connection failed."
          );

          setStatus("Connection error");
          setLoading(false);
        }
      };

      client.onstatechange = (state) => {
        if (disconnectingRef.current) return;

        console.log(
          "[MT ACCESS] Guacamole state changed:",
          state
        );

        if (state === Guacamole.Client.State.CONNECTED) {
          setStatus("Connected");
          setLoading(false);
          setError("");
        } else if (
          state === Guacamole.Client.State.DISCONNECTED
        ) {
          setStatus("Disconnected");
          setLoading(false);
        } else if (
          state === Guacamole.Client.State.WAITING
        ) {
          setStatus("Waiting for remote desktop");
        } else if (
          state === Guacamole.Client.State.CONNECTING
        ) {
          setStatus("Connecting");
        }
      };

      const mouse = new Guacamole.Mouse(displayElement);

      mouse.onmousedown = mouse.onmouseup = mouse.onmousemove = (
        mouseState
      ) => {
        if (clientRef.current === client) {
          client.sendMouseState(mouseState);
        }
      };

      const keyboard = new Guacamole.Keyboard(document);

      keyboard.onkeydown = (keysym) => {
        if (clientRef.current === client) {
          client.sendKeyEvent(1, keysym);
        }
      };

      keyboard.onkeyup = (keysym) => {
        if (clientRef.current === client) {
          client.sendKeyEvent(0, keysym);
        }
      };

      keyboardRef.current = keyboard;

      const parameters = new URLSearchParams({
        GUAC_DATA_SOURCE: dataSource,
        GUAC_ID: connectionId,
        GUAC_TYPE: "c",
        GUAC_WIDTH: String(
          displayRef.current.clientWidth || window.innerWidth
        ),
        GUAC_HEIGHT: String(
          displayRef.current.clientHeight || window.innerHeight
        ),
        GUAC_DPI: "96",
        GUAC_TIMEZONE:
          Intl.DateTimeFormat().resolvedOptions().timeZone,

        // Apache Guacamole expects the authentication token
        // under the parameter name "token".
        token: auth.authToken,
      });

      console.log("[MT ACCESS] Opening remote desktop tunnel");

      client.connect(parameters.toString());

    } catch (err) {
      console.error(
        "[MT ACCESS] Viewer connection failed:",
        err
      );

      if (!disconnectingRef.current) {
        setError(
          err.message || "Unable to connect to remote desktop."
        );

        setStatus("Connection failed");
        setLoading(false);
      }
    }
  }, [token, cleanupViewer]);

  useEffect(() => {
    connectViewer();

    return () => {
      cleanupViewer();
    };
  }, [connectViewer, cleanupViewer]);

  async function confirmDisconnect() {
    setShowDisconnect(false);

    // Close only the Guacamole viewer connection.
    cleanupViewer();

    setStatus("Disconnected");
    setLoading(false);

    try {
      await apiRequest(
        "/api/sessions/disconnect",
        { method: "POST" },
        token
      );
    } catch (err) {
      console.error(
        "Disconnect audit request failed:",
        err
      );
    }

    try {
      const user = await apiRequest(
        "/api/auth/me",
        {},
        token
      );

      const userKey =
        user?.id || user?.client_code || "client";

      localStorage.setItem(
        `mt-access-remote-${userKey}`,
        "false"
      );
    } catch (err) {
      console.error(
        "Unable to update remote access preference:",
        err
      );
    }

    // The MT4/MT5 application process remains running.
    onBack();
  }

  return (
    <div className="dashboard-layout">
      <main
        className="dashboard-main"
        style={{ width: "100%" }}
      >
        <header className="topbar">
          <div className="topbar-left">
            <SecondaryAction onClick={onBack}>
              <ArrowLeft size={15} />
              Back to Dashboard
            </SecondaryAction>
          </div>

          <div className="topbar-right">
            <span className="admin-badge">
              <ShieldCheck size={14} />
              Secure Remote Access
            </span>
          </div>
        </header>

        <div className="page-content">
          <div className="welcome-row">
            <div>
              <p className="eyebrow">REMOTE APPLICATION</p>
              <h1>Trading Workspace</h1>

              <p className="page-subtitle">
                Session ID: {sessionId || "Not available"}
              </p>
            </div>

            <div
              style={{
                display: "flex",
                gap: "10px",
              }}
            >
              <SecondaryAction onClick={connectViewer}>
                <RefreshCw size={15} />
                Reconnect
              </SecondaryAction>

              <PrimaryAction
                onClick={() => setShowDisconnect(true)}
              >
                <Unplug size={15} />
                Disconnect
              </PrimaryAction>
            </div>
          </div>

          <Notice message={error} error />

          <section
            className="content-card"
            style={{ marginTop: "20px" }}
          >
            <div className="card-heading">
              <div>
                <h3>Remote Desktop Viewer</h3>
                <p>{status}</p>
              </div>

              <Monitor size={22} />
            </div>

            {loading && (
              <div
                style={{
                  padding: "20px",
                  textAlign: "center",
                  color: "#64748b",
                }}
              >
                <RefreshCw size={25} />
                <p>
                  Connecting to your trading workspace...
                </p>
              </div>
            )}

            <div
              ref={displayRef}
              style={{
                width: "100%",
                height: "70vh",
                minHeight: "400px",
                overflow: "auto",
                background: "#111827",
                borderRadius: "8px",
              }}
            />

            {!loading && error && (
              <div style={{ padding: "15px" }}>
                <SecondaryAction onClick={connectViewer}>
                  <RefreshCw size={15} />
                  Retry Connection
                </SecondaryAction>
              </div>
            )}
          </section>
        </div>
      </main>

      {showDisconnect && (
        <div
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setShowDisconnect(false);
            }
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 2000,
            background: "rgba(15,23,42,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "15px",
          }}
        >
          <div
            style={{
              background: "#fff",
              borderRadius: "12px",
              padding: "24px",
              width: "100%",
              maxWidth: "420px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <h3>Disconnect Remote Access?</h3>

              <button
                type="button"
                onClick={() => setShowDisconnect(false)}
                style={{
                  border: 0,
                  background: "none",
                  cursor: "pointer",
                }}
              >
                <X size={20} />
              </button>
            </div>

            <p
              style={{
                color: "#64748b",
                lineHeight: 1.6,
              }}
            >
              This will close your remote desktop connection.
              Your MT4/MT5 application will continue running
              on the server.
            </p>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "10px",
                marginTop: "20px",
              }}
            >
              <SecondaryAction
                onClick={() => setShowDisconnect(false)}
              >
                Cancel
              </SecondaryAction>

              <PrimaryAction onClick={confirmDisconnect}>
                Confirm Disconnect
              </PrimaryAction>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
