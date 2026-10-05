import { useEffect, useState } from "react";
import { api } from "../api";
import { date, Notice, PageTitle } from "../components";

export default function Admin() {
  const [data, setData] = useState(null),
    [query, setQuery] = useState(""),
    [error, setError] = useState(null),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    try {
      setData(await api(`/admin?q=${encodeURIComponent(query)}`));
    } catch (e) {
      setError(e);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function act(path, method, body, confirmation) {
    if (confirmation && !window.confirm(confirmation)) return;
    setBusy(true);
    setError(null);
    setMessage("");
    try {
      await api(path, { method, body });
      setMessage("Changes saved.");
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="SYSTEM MANAGEMENT"
        title="Administration"
        description="Manage accounts, monitor conversion activity, and configure system limits."
      />
      <Notice error={error} message={message} />
      {!data ? (
        <p>Loading administration…</p>
      ) : (
        <>
          <div className="stat-grid">
            {Object.entries(data.stats).map(([key, value]) => (
              <div className="stat" key={key}>
                <b>{value}</b>
                <span>{key.replaceAll("_", " ")}</span>
              </div>
            ))}
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Accounts</h2>
              <form
                className="inline-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  load();
                }}
              >
                <input
                  aria-label="Search accounts"
                  placeholder="Search name or email"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button className="button secondary">Search</button>
              </form>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.name}</td>
                      <td>{u.email}</td>
                      <td>{u.role}</td>
                      <td>
                        <span className="badge">
                          {!u.active
                            ? "Suspended"
                            : !u.verified
                              ? "Unverified"
                              : "Active"}
                        </span>
                      </td>
                      <td>
                        {u.role !== "admin" && (
                          <div className="row-actions">
                            <button
                              disabled={busy}
                              className="button small secondary"
                              onClick={() =>
                                act(`/admin/users/${u.id}`, "PATCH", {
                                  active: !u.active,
                                })
                              }
                            >
                              {u.active ? "Suspend" : "Activate"}
                            </button>
                            <button
                              disabled={busy}
                              className="button small danger"
                              onClick={() =>
                                act(
                                  `/admin/users/${u.id}`,
                                  "DELETE",
                                  undefined,
                                  `Permanently delete ${u.email} and all related records?`,
                                )
                              }
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel">
            <h2>System limits</h2>
            <form
              key={JSON.stringify(data.config)}
              onSubmit={(e) => {
                e.preventDefault();
                const values = Object.fromEntries(
                  [...new FormData(e.currentTarget)].map(([k, v]) => [
                    k,
                    Number(v),
                  ]),
                );
                act("/admin/config", "PUT", values);
              }}
            >
              <div className="form-grid three">
                <label>
                  Maximum upload (MB)
                  <input
                    type="number"
                    name="max_upload_mb"
                    min={1}
                    max={50}
                    defaultValue={data.config.max_upload_mb}
                    required
                  />
                </label>
                <label>
                  Nominal inference threshold
                  <input
                    type="number"
                    name="nominal_threshold"
                    min={1}
                    max={1000}
                    defaultValue={data.config.nominal_threshold}
                    required
                  />
                </label>
                <label>
                  File retention (hours)
                  <input
                    type="number"
                    name="retention_hours"
                    min={1}
                    max={168}
                    defaultValue={data.config.retention_hours}
                    required
                  />
                </label>
              </div>
              <button className="button" disabled={busy}>
                Save limits
              </button>
            </form>
          </section>
          <section className="panel">
            <h2>Recent conversion activity</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Direction</th>
                    <th>Instances</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.activity.map((a) => (
                    <tr key={a.id}>
                      <td>{a.filename}</td>
                      <td>
                        {a.source_format} → {a.target_format}
                      </td>
                      <td>{a.instance_count}</td>
                      <td>{date(a.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data.activity.length && (
              <p className="muted">No conversions yet.</p>
            )}
          </section>
          <section className="panel">
            <h2>Validation, email & access logs</h2>
            <div className="log-list">
              {data.logs.map((log) => (
                <div key={log.id}>
                  <span className="badge">{log.kind}</span>
                  <p>
                    {log.message}
                    {log.details.errors?.map((e, i) => (
                      <small key={i}>
                        Line {e.line} · {e.severity} · {e.message}
                      </small>
                    ))}
                  </p>
                  <time>{date(log.created_at)}</time>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </>
  );
}
