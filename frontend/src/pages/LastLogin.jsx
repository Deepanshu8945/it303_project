import { useEffect, useState } from "react";
import { api } from "../api";
import { date, Notice, PageTitle, useAuth } from "../components";

export default function LastLogin() {
  const { user } = useAuth();
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems((await api("/auth/login-history")).items);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="YOUR ACCOUNT"
        title="Last login"
        description={`Successful sign-ins for ${user.email}. Times use your device's local time zone.`}
        action={
          <button
            className="button secondary"
            onClick={load}
            disabled={loading}
          >
            Refresh details
          </button>
        }
      />
      <Notice error={error} />
      <section className="panel" aria-label="Your login history">
        <h2>Your login history</h2>
        {loading ? (
          <p role="status">Loading login history…</p>
        ) : (
          !error &&
          items &&
          (items.length === 0 ? (
            <p className="muted">
              No login details recorded yet. Sign out and sign in again to
              record your next login.
            </p>
          ) : (
            <div className="table-wrap">
              <table
                className="login-history-table"
                aria-label="Successful sign-ins"
              >
                <thead>
                  <tr>
                    <th>Date and time</th>
                    <th>IP address</th>
                    <th>Browser / device information</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <time dateTime={item.logged_in_at}>
                          {date(item.logged_in_at)}
                        </time>
                      </td>
                      <td>{item.ip_address || "Unavailable"}</td>
                      <td>{item.user_agent || "Unavailable"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
        <p className="footnote">
          Your latest 100 successful sign-ins, newest first. Failed attempts and
          session refreshes are excluded.
        </p>
      </section>
      <p className="muted login-note">
        The IP address is the address seen by the server; local development may
        show a loopback address.
      </p>
    </>
  );
}
