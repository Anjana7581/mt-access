
export function Notice({ message, error = false }) {
  if (!message) return null;

  return (
    <div
      style={{
        padding: "12px 15px",
        margin: "15px 0",
        borderRadius: "8px",
        background: error ? "#fff0f0" : "#eaf8ef",
        color: error ? "#b42318" : "#16733b",
        fontSize: "14px",
      }}
    >
      {message}
    </div>
  );
}

export function PrimaryAction({ children, ...props }) {
  return (
    <button
      type="button"
      {...props}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        padding: "10px 15px",
        border: 0,
        borderRadius: "7px",
        background: "#2463eb",
        color: "#fff",
        fontSize: "13px",
        fontWeight: 600,
        cursor: "pointer",
        ...props.style,
      }}
    >
      {children}
    </button>
  );
}

export function SecondaryAction({ children, ...props }) {
  return (
    <button
      type="button"
      {...props}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        padding: "9px 13px",
        border: "1px solid #dce3ec",
        borderRadius: "7px",
        background: "#fff",
        color: "#334155",
        fontSize: "13px",
        cursor: "pointer",
        ...props.style,
      }}
    >
      {children}
    </button>
  );
}
