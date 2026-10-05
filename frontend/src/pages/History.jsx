import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Trash2, Search } from "lucide-react";
import { api, download } from "../api";
import { date, size, Empty, Notice, PageTitle } from "../components";

export default function History() {
  const [items, setItems] = useState(null),
    [query, setQuery] = useState(""),
    [source, setSource] = useState(""),
    [error, setError] = useState(null);
  async function load() {
    setError(null);
    try {
      setItems(
        await api(`/history?q=${encodeURIComponent(query)}&source=${source}`),
      );
    } catch (e) {
      setError(e);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function remove(item) {
    if (
      !window.confirm(
        `Delete the history and converted output for ${item.filename}?`,
      )
    )
      return;
    try {
      await api(`/history/${item.id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="YOUR RECORDS"
        title="Conversion history"
        description="Every completed conversion, in one place. Only your records are shown."
        action={
          <Link className="button" to="/converter">
            New conversion →
          </Link>
        }
      />
      <Notice error={error} />
      <section className="panel">
        <form
          className="filter-bar"
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
        >
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search file name"
              placeholder="Search by file name…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            aria-label="Source format"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="">All formats</option>
            <option value="csv">CSV → ARFF</option>
            <option value="arff">ARFF → CSV</option>
          </select>
          <button className="button secondary">Apply filters</button>
        </form>
        {!items ? (
          <p>Loading history…</p>
        ) : items.length === 0 ? (
          <Empty>No conversions match. Upload a dataset to get started.</Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File / completed</th>
                  <th>Conversion</th>
                  <th>Size</th>
                  <th>Instances / attributes</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <b>{r.filename}</b>
                      <small className="table-sub">{date(r.created_at)}</small>
                    </td>
                    <td>
                      {r.source_format.toUpperCase()} →{" "}
                      {r.target_format.toUpperCase()}
                    </td>
                    <td>{size(r.size)}</td>
                    <td>
                      {r.instance_count} / {r.attribute_count}
                    </td>
                    <td>
                      <span className="badge">{r.status}</span>
                      <small className="table-sub">
                        {r.download_available
                          ? "Download available"
                          : "File expired"}
                      </small>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          aria-label={`Download ${r.filename}`}
                          className="icon-button"
                          disabled={!r.download_available}
                          onClick={() =>
                            download(
                              r.id,
                              r.filename.replace(
                                /\.[^.]+$/,
                                `.${r.target_format}`,
                              ),
                            ).catch(setError)
                          }
                        >
                          <Download size={17} />
                        </button>
                        <button
                          aria-label={`Delete ${r.filename}`}
                          className="icon-button danger-text"
                          onClick={() => remove(r)}
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="footnote">
          Latest 500 matching records. File expiry removes the dataset; history
          metadata remains until you delete it.
        </p>
      </section>
    </>
  );
}
