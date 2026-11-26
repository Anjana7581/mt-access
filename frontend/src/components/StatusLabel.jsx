
export default function StatusLabel({ value }) {
  const active = ["active", "online", "running"].includes(
    String(value || "").toLowerCase()
  );

  return (
    <span style={{
      display: "inline-block",
      padding: "5px 9px",
      borderRadius: "20px",
      fontSize: "11px",
      background: active ? "#e8f7ed" : "#f1f3f6",
      color: active ? "#16803c" : "#64748b",
      textTransform: "capitalize",
    }}>
      {value || "Unknown"}
    </span>
  );
}
