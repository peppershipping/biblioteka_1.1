import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAppSelector } from "../store";

export default function PrivateRoute() {
  const { user, status } = useAppSelector((s) => s.auth);
  const location = useLocation();

  if (status !== "ready") return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}
