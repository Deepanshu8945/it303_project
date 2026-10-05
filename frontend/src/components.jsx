import { createContext, useContext, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import {
  ArrowLeftRight,
  LayoutDashboard,
  FileUp,
  History,
  Settings,
  ShieldCheck,
  LogOut,
  ArrowUpRight,
} from "lucide-react";
import { api, clearSession } from "./api";

export const AuthContext = createContext();
export const useAuth = () => useContext(AuthContext);
export const participants = [
  "Aayush Sarraf",
  "Aditya Raj",
  "Deepanshu Kumar",
  "Dhruv Agarwal",
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api("/auth/me")
      .then(setUser)
      .catch(() => clearSession())
      .finally(() => setLoading(false));
    const expire = () => setUser(null);
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  return (
    <AuthContext.Provider value={{ user, setUser, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function Brand() {
  return (
    <Link className="brand" to="/">
      <span className="brand-icon">
        <ArrowLeftRight size={20} />
      </span>
      <span>
        File Converter<small>CSV ↔ ARFF</small>
      </span>
    </Link>
  );
}

export function Footer() {
  return (
    <footer>
      <span>
        © {new Date().getFullYear()} File Converter System. All Rights
        Reserved.
        <br />
        Contact:{" "}
        <a href="mailto:dk.tech853@gmail.com" className="footer-contact">
          dk.tech853@gmail.com
        </a>
      </span>
      <span>
        Developed by {participants.join(", ")}
        <br />
        Course: Software Engineering - IT303
      </span>
    </footer>
  );
}

export function PublicLayout() {
  const { user } = useAuth();
  return (
    <>
      <header className="public-header">
        <Brand />
        <nav>
          <Link
            className="button secondary"
            to={user ? "/dashboard" : "/login"}
          >
            {user ? "Open workspace" : "Sign in"} <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <Outlet />
      <Footer />
    </>
  );
}

export function Protected({ admin = false }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Loading your workspace…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin")
    return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

export function WorkspaceLayout() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      clearSession();
      setUser(null);
      navigate("/login");
    } catch (e) {
      setError(e);
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <span className="nav-label">YOUR WORKSPACE</span>
        <nav>
          <NavLink to="/dashboard">
            <LayoutDashboard size={18} />
            Overview
          </NavLink>
          <NavLink to="/converter">
            <FileUp size={18} />
            File converter
          </NavLink>
          <NavLink to="/history">
            <History size={18} />
            Conversion history
          </NavLink>
          <NavLink to="/profile">
            <Settings size={18} />
            Profile & security
          </NavLink>
          {user.role === "admin" && (
            <NavLink to="/admin">
              <ShieldCheck size={18} />
              Administration
            </NavLink>
          )}
          <button
            className="mobile-signout icon-button"
            onClick={logout}
            aria-label="Sign out on mobile"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="user-card">
            <span className="avatar">{user.name[0]}</span>
            <div>
              <b>{user.name}</b>
              <small>
                {user.role === "admin" ? "Administrator" : "Registered user"}
              </small>
            </div>
            <button
              className="icon-button"
              onClick={logout}
              aria-label="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-header">
          <span>
            IT303 <span className="muted">/ Software Engineering</span>
          </span>
        </header>
        <main className="workspace-content">
          <Notice error={error} />
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}

export function Notice({ error, message }) {
  if (!error && !message) return null;
  return (
    <div
      role={error ? "alert" : "status"}
      className={`notice ${error ? "error" : "success"}`}
    >
      {error?.message || message}
      {error?.defects?.length > 0 && (
        <ul>
          {error.defects.map((d, i) => (
            <li key={i}>
              {d.line ? `Line ${d.line}: ` : ""}
              {d.attribute ? `${d.attribute}: ` : ""}
              {d.field ? `${d.field}: ` : ""}
              {d.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function PageTitle({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function Empty({ children }) {
  return (
    <div className="empty">
      <History size={28} />
      <p>{children}</p>
    </div>
  );
}

export const date = (value) => new Date(value).toLocaleString();
export const size = (value) =>
  value < 1024 ? `${value} B` : `${(value / 1024).toFixed(1)} KB`;
