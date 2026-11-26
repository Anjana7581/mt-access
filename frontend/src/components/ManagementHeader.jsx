
export default function ManagementHeader({ title, description, action }) {
  return (
    <div className="welcome-row">
      <div>
        <h1>{title}</h1>
        <p className="page-subtitle">{description}</p>
      </div>
      {action}
    </div>
  );
}
