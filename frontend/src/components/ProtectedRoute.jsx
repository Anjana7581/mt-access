
export default function ProtectedRoute({ user, role, children }) {
  if (!user) return null;

  if (user.role !== role) {
    return (
      <div className="loading-screen">
        You are not authorized to access this page.
      </div>
    );
  }

  return children;
}
