import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearSession } from "../api";
import { Notice, PageTitle, useAuth } from "../components";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [error, setError] = useState(null),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(e, kind) {
    e.preventDefault();
    if (
      kind === "delete" &&
      !window.confirm(
        "Permanently delete your account, history, and stored files?",
      )
    )
      return;
    const body = Object.fromEntries(new FormData(e.currentTarget));
    const form = e.currentTarget;
    setError(null);
    setMessage("");
    setBusy(true);
    try {
      if (body.confirm !== undefined && body.password !== body.confirm)
        throw new Error("Passwords do not match.");
      const result = await api(
        kind === "password" ? "/profile/password" : "/profile",
        {
          method:
            kind === "delete"
              ? "DELETE"
              : kind === "password"
                ? "POST"
                : "PATCH",
          body,
        },
      );
      if (kind !== "profile" || !result.user.verified) {
        sessionStorage.setItem("account-message", result.message);
        clearSession();
        setUser(null);
        navigate("/login", { state: { message: result.message } });
      } else {
        setUser(result.user);
        setMessage(result.message);
        form.querySelector("[name=current_password]").value = "";
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="YOUR ACCOUNT"
        title="Profile & security"
        description="Keep your details current and your account secure."
      />
      <Notice error={error} message={message} />
      <div className="profile-grid">
        <section className="panel">
          <h2>Profile information</h2>
          <p className="muted">
            Changing your email requires verification and signs you out.
          </p>
          <form onSubmit={(e) => submit(e, "profile")}>
            <label>
              Full name
              <input
                name="name"
                defaultValue={user.name}
                required
                maxLength={100}
              />
            </label>
            <label>
              Email address
              <input
                name="email"
                type="email"
                defaultValue={user.email}
                required
              />
            </label>
            <label>
              Current password
              <input
                name="current_password"
                type="password"
                required
                autoComplete="current-password"
              />
            </label>
            <button className="button" disabled={busy}>
              Save profile
            </button>
          </form>
        </section>
        <section className="panel">
          <h2>Change password</h2>
          <p className="muted">
            All sessions will be signed out after a password change.
          </p>
          <form onSubmit={(e) => submit(e, "password")}>
            <label>
              Current password
              <input
                name="current_password"
                type="password"
                required
                autoComplete="current-password"
              />
            </label>
            <label>
              New password
              <input
                name="password"
                type="password"
                minLength={10}
                maxLength={72}
                required
                autoComplete="new-password"
              />
            </label>
            <label>
              Confirm new password
              <input
                name="confirm"
                type="password"
                required
                autoComplete="new-password"
              />
            </label>
            <small className="muted">
              Use at least 10 characters with uppercase, lowercase, and a
              number.
            </small>
            <button className="button" disabled={busy}>
              Change password
            </button>
          </form>
        </section>
      </div>
      {user.role !== "admin" && (
        <section className="panel danger-zone">
          <h2>Delete account</h2>
          <p>
            This permanently removes your account, conversion history, and
            files.
          </p>
          <form onSubmit={(e) => submit(e, "delete")}>
            <label>
              Current password
              <input
                name="current_password"
                type="password"
                required
                autoComplete="current-password"
              />
            </label>
            <button className="button danger" disabled={busy}>
              Delete my account
            </button>
          </form>
        </section>
      )}
    </>
  );
}
