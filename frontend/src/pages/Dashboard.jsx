import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileUp,
  ArrowLeftRight,
  Layers,
  Download,
} from "lucide-react";
import { api } from "../api";
import { date, Empty, Notice, PageTitle, useAuth } from "../components";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null),
    [error, setError] = useState(null);
  useEffect(() => {
    api("/dashboard").then(setData).catch(setError);
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="YOUR OVERVIEW"
        title={`Welcome, ${user.name.split(" ")[0]}.`}
        description="A clear view of your data preparation work."
        action={
          <Link className="button" to="/converter">
            <FileUp size={17} />
            New conversion
          </Link>
        }
      />
      <Notice error={error} />
      {!data && !error && <p>Loading your overview…</p>}
      {data && (
        <>
          <div className="stat-grid">
            {[
              [ArrowLeftRight, data.total, "Completed conversions"],
              [Layers, data.instances.toLocaleString(), "Instances processed"],
              [Download, data.available, "Downloads in retention window"],
            ].map(([Icon, n, label]) => (
              <div className="stat" key={label}>
                <Icon size={20} />
                <b>{n}</b>
                <span>{label}</span>
              </div>
            ))}
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Recent conversions</h2>
              <Link className="text-link" to="/history">
                View history ↗
              </Link>
            </div>
            {data.recent.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>File name</th>
                      <th>Conversion</th>
                      <th>Instances</th>
                      <th>Completed</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <b>{r.filename}</b>
                        </td>
                        <td>
                          {r.source_format.toUpperCase()} →{" "}
                          {r.target_format.toUpperCase()}
                        </td>
                        <td>{r.instance_count}</td>
                        <td>{date(r.created_at)}</td>
                        <td>
                          <span className="badge">Completed</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty>Your first conversion will appear here.</Empty>
            )}
          </section>
        </>
      )}
    </>
  );
}
