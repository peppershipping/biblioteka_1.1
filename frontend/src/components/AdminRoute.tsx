import { Navigate, Outlet } from "react-router-dom";
import { useAppSelector } from "../store";

/** Маршруты только для роли admin (серверная проверка прав всё равно выполняется на API). */
export default function AdminRoute() {
  const { user, status } = useAppSelector((s) => s.auth);

  if (status !== "ready") return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}
