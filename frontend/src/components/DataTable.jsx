
export function DataTable({ columns, children, loading, empty }) {
  return (
    <div className="content-card" style={{ marginTop: "20px", overflowX: "auto" }}>
      {loading ? (
        <p style={{ padding: "25px" }}>Loading data...</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  style={{
                    padding: "14px 12px",
                    borderBottom: "1px solid #e8edf3",
                    fontSize: "13px",
                    color: "#64748b",
                    whiteSpace: "nowrap",
                  }}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {children}
            {!loading && empty && (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: "25px", textAlign: "center", color: "#64748b" }}
                >
                  {empty}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function TableCell({ children }) {
  return (
    <td style={{
      padding: "14px 12px",
      borderBottom: "1px solid #edf0f4",
      fontSize: "13px",
      verticalAlign: "middle",
    }}>
      {children}
    </td>
  );
}

export function ActionButton({ title, onClick, children, danger = false }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      style={{
        border: "1px solid #e2e8f0",
        background: danger ? "#fff5f5" : "#fff",
        color: danger ? "#c0392b" : "#334155",
        borderRadius: "6px",
        padding: "7px",
        marginRight: "5px",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}
