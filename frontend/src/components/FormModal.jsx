
import { X } from "lucide-react";

export function FormModal({ title, onClose, children }) {
  return (
    <div
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(15, 23, 42, 0.55)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "15px",
      }}
    >
      <div style={{
        width: "100%",
        maxWidth: "500px",
        maxHeight: "90vh",
        overflowY: "auto",
        background: "#fff",
        borderRadius: "12px",
        padding: "24px",
        boxShadow: "0 15px 50px rgba(0,0,0,0.2)",
      }}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}>
          <h2 style={{ margin: 0, fontSize: "19px" }}>{title}</h2>
          <button type="button" onClick={onClose} style={{ border: 0, background: "none" }}>
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const fieldStyle = {
  width: "100%",
  padding: "11px 12px",
  border: "1px solid #dce3ec",
  borderRadius: "7px",
  marginTop: "6px",
  marginBottom: "15px",
  fontSize: "13px",
  background: "#fff",
};

export function FormField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  options,
}) {
  return (
    <div>
      <label style={{ fontSize: "13px", fontWeight: 600 }}>{label}</label>
      {options ? (
        <select
          style={fieldStyle}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          style={fieldStyle}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
        />
      )}
    </div>
  );
}

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
