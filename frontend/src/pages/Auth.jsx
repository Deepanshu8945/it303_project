import { useEffect, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { api, saveSession } from "../api";
import { Notice, useAuth } from "../components";

const titles = {
  login: "Welcome back.",
  register: "Create your account.",
  forgot: "Reset your password.",
  reset: "Choose a new password.",
  verify: "Verify your email.",
  resend: "Get a new verification link.",
};

export default function Auth({ mode }) {
  const location = useLocation();
  const [error, setError] = useState(null),
    [message, setMessage] = useState(
      location.state?.message ||
        sessionStorage.getItem("account-message") ||
        "",
    ),
    [busy, setBusy] = useState(false);
  const [search] = useSearchParams();
  const { setUser } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    sessionStorage.removeItem("account-message");
  }, []);
  async function submit(event) {
    event.preventDefault();
    setError(null);
    setMessage("");
    setBusy(true);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (values.confirm !== undefined && values.password !== values.confirm)
        throw new Error("Passwords do not match.");
      const endpoint = {
        login: "login",
        register: "register",
        forgot: "forgot-password",
        reset: "reset-password",
        verify: "verify",
        resend: "resend-verification",
      }[mode];
      const result = await api(`/auth/${endpoint}`, {
        method: "POST",
        body: { ...values, token: search.get("token") || "" },
      });
      if (mode === "login") {
        saveSession(result);
        setUser(result.user);
        navigate("/dashboard");
      } else setMessage(result.message);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <div className="auth-intro">
        <span className="eyebrow">FILE CONVERTER SYSTEM</span>
        <h1>
          Less formatting.
          <br />
          <em>More possibility.</em>
        </h1>
        <p>One workspace for preparing your CSV and ARFF datasets.</p>
        <div className="auth-note">
          <ShieldCheck />
          <p>
            Secure accounts.
            <br />A private conversion history.
            <br />
            Control over every attribute.
          </p>
        </div>
      </div>
      <section className="auth-card">
        <span className="eyebrow">YOUR WORKSPACE STARTS HERE</span>
        <h2>{titles[mode]}</h2>
        <p className="muted">
          {mode === "verify"
            ? "Confirm your email to activate your account."
            : "Use your email to access the File Converter System."}
        </p>
        <Notice error={error} message={message} />
        <form onSubmit={submit}>
          {mode === "register" && (
            <label>
              Full name
              <input name="name" required maxLength={100} autoComplete="name" />
            </label>
          )}
          {["login", "register", "forgot", "resend"].includes(mode) && (
            <label>
              Email address
              <input
                name="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@example.com"
              />
            </label>
          )}
          {["login", "register", "reset"].includes(mode) && (
            <label>
              Password
              <input
                name="password"
                type="password"
                required
                minLength={mode === "login" ? 1 : 10}
                maxLength={72}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
              />
            </label>
          )}
          {["register", "reset"].includes(mode) && (
            <>
              <small className="muted">
                At least 10 characters, with uppercase, lowercase, and a number.
              </small>
              <label>
                Confirm password
                <input
                  name="confirm"
                  type="password"
                  required
                  minLength={10}
                  autoComplete="new-password"
                />
              </label>
            </>
          )}
          {mode === "login" && (
            <Link className="text-link form-link" to="/forgot">
              Forgot password?
            </Link>
          )}
          <button className="button full" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Sign in"
                : mode === "register"
                  ? "Create account"
                  : mode === "verify"
                    ? "Verify email"
                    : mode === "reset"
                      ? "Save new password"
                      : "Send link"}
            <ArrowRight size={17} />
          </button>
        </form>
        <div className="auth-links">
          {mode === "login" ? (
            <>
              <span>
                New here? <Link to="/register">Create an account</Link>
              </span>
              <Link to="/resend">Resend verification email</Link>
            </>
          ) : (
            <Link to="/login">Back to sign in</Link>
          )}
        </div>
      </section>
    </main>
  );
}
