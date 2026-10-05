import { useEffect, useRef, useState } from "react";
import {
  Upload,
  ArrowRight,
  Download,
  Check,
  FileSpreadsheet,
} from "lucide-react";
import { api, download } from "../api";
import { Notice, PageTitle, size } from "../components";

export default function Converter() {
  const [file, setFile] = useState(null),
    [options, setOptions] = useState({
      delimiter: ",",
      quote: '"',
      header: true,
      relation: "",
    });
  const [upload, setUpload] = useState(null),
    [attributes, setAttributes] = useState([]),
    [result, setResult] = useState(null);
  const [limits, setLimits] = useState(null),
    [error, setError] = useState(null),
    [busy, setBusy] = useState(false),
    [drag, setDrag] = useState(false);
  const input = useRef();
  useEffect(() => {
    api("/limits").then(setLimits).catch(setError);
  }, []);
  function choose(value) {
    setFile(value);
    setUpload(null);
    setResult(null);
    setError(null);
  }
  function option(key, value) {
    setOptions((o) => ({ ...o, [key]: value }));
    setUpload(null);
    setResult(null);
  }
  async function analyze(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    setResult(null);
    setUpload(null);
    try {
      if (!file) throw new Error("Choose a CSV or ARFF file first.");
      if (limits && file.size > limits.max_upload_mb * 1024 * 1024)
        throw new Error(`Choose a file under ${limits.max_upload_mb} MB.`);
      const body = new FormData();
      body.append("file", file);
      body.append("options", JSON.stringify(options));
      const data = await api("/uploads", { method: "POST", body });
      setUpload(data);
      setAttributes(data.attributes);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function convert() {
    setError(null);
    setBusy(true);
    setResult(null);
    try {
      setResult(
        await api("/conversions", {
          method: "POST",
          body: {
            upload_id: upload.upload_id,
            attributes,
            relation: upload.relation,
          },
        }),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function edit(index, changes) {
    setAttributes((a) =>
      a.map((v, i) => (i === index ? { ...v, ...changes } : v)),
    );
    setResult(null);
  }
  return (
    <>
      <PageTitle
        eyebrow="DATA PREPARATION"
        title="File converter"
        description="A little structure goes a long way. Bring your dataset and review every detail."
      />
      <div className="steps">
        {["Upload & configure", "Review schema", "Preview & download"].map(
          (text, i) => (
            <div
              key={text}
              className={(result ? 2 : upload ? 1 : 0) >= i ? "active" : ""}
            >
              <span>
                {(result ? 2 : upload ? 1 : 0) > i ? (
                  <Check size={14} />
                ) : (
                  `0${i + 1}`
                )}
              </span>
              {text}
              {i < 2 && <ArrowRight size={16} />}
            </div>
          ),
        )}
      </div>
      <Notice error={error} />
      <div className="converter-grid">
        <section className="panel upload-panel">
          <div className="panel-heading">
            <h2>
              01 <span>Upload your dataset</span>
            </h2>
            <span className="file-tag">CSV / ARFF</span>
          </div>
          <form onSubmit={analyze}>
            <input
              ref={input}
              type="file"
              accept=".csv,.arff"
              className="visually-hidden"
              onChange={(e) => choose(e.target.files[0])}
              aria-label="Dataset file"
            />
            <button
              type="button"
              disabled={busy}
              className={`dropzone ${drag ? "dragging" : ""}`}
              onClick={() => input.current.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                if (!busy) choose(e.dataTransfer.files[0]);
              }}
            >
              <span className="upload-icon">
                {file ? <FileSpreadsheet /> : <Upload />}
              </span>
              <b>{file ? file.name : "Drop your dataset here"}</b>
              <span>
                {file
                  ? `${size(file.size)} · Click to choose a different file`
                  : "or click to browse your files"}
              </span>
              <small>
                UTF-8 or ASCII ·{" "}
                {limits
                  ? `Up to ${limits.max_upload_mb} MB`
                  : "Loading file limit…"}
              </small>
            </button>
            <div className="panel-heading options-heading">
              <h3>Parsing options</h3>
              <span className="muted">Applied on upload</span>
            </div>
            <div className="form-grid">
              <label>
                Delimiter
                <select
                  value={options.delimiter}
                  onChange={(e) => option("delimiter", e.target.value)}
                >
                  <option value=",">Comma (,)</option>
                  <option value=";">Semicolon (;)</option>
                  <option value={"\t"}>Tab</option>
                  <option value="|">Pipe (|)</option>
                </select>
              </label>
              <label>
                Quote character
                <select
                  value={options.quote}
                  onChange={(e) => option("quote", e.target.value)}
                >
                  <option value={'"'}>Double quote (")</option>
                  <option value="'">Single quote (')</option>
                </select>
              </label>
              <label className="span-two">
                Relation name
                <input
                  placeholder="Defaults to your file name"
                  value={options.relation}
                  onChange={(e) => option("relation", e.target.value)}
                  maxLength={200}
                />
              </label>
            </div>
            <label className="check-label">
              <input
                type="checkbox"
                checked={options.header}
                onChange={(e) => option("header", e.target.checked)}
              />
              First CSV row contains attribute names
            </label>
            <button className="button full" disabled={busy || !file}>
              {busy ? "Processing dataset…" : "Upload & review schema"}
              <ArrowRight size={17} />
            </button>
          </form>
        </section>
        <aside className="guidance">
          <span className="eyebrow">BEFORE YOU CONVERT</span>
          <h3>
            Good data starts
            <br />
            with a clear schema.
          </h3>
          <p>
            Your file is parsed on the server. You’ll see the detected format,
            column names, and inferred types before converting.
          </p>
          <ul>
            <li>
              <Check size={16} />
              Numeric precision is preserved
            </li>
            <li>
              <Check size={16} />
              Empty CSV fields become missing values
            </li>
            <li>
              <Check size={16} />
              Errors include the affected line
            </li>
          </ul>
          <div className="guidance-note">
            Downloads remain available for{" "}
            {limits?.retention_hours || "the configured"} hours. Your conversion
            history stays until you delete it.
          </div>
        </aside>
      </div>
      {upload && (
        <section className="panel schema-panel">
          <div className="panel-heading">
            <h2>
              02 <span>Review & confirm schema</span>
            </h2>
            <span className="badge">
              {upload.source_format.toUpperCase()} →{" "}
              {upload.target_format.toUpperCase()}
            </span>
          </div>
          <p className="muted">
            {upload.instance_count.toLocaleString()} instances ·{" "}
            {upload.attribute_count} attributes · Relation: {upload.relation}
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Attribute name</th>
                  <th>Type</th>
                  <th>Values / date pattern</th>
                </tr>
              </thead>
              <tbody>
                {attributes.map((a, i) => (
                  <tr key={i}>
                    <td>{String(i + 1).padStart(2, "0")}</td>
                    <td>
                      <input
                        aria-label={`Attribute ${i + 1} name`}
                        value={a.name}
                        onChange={(e) => edit(i, { name: e.target.value })}
                        maxLength={200}
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`Attribute ${i + 1} type`}
                        value={a.type}
                        onChange={(e) =>
                          edit(i, {
                            type: e.target.value,
                            values: [],
                            date_format: null,
                          })
                        }
                      >
                        {["numeric", "nominal", "date", "string"].map((t) => (
                          <option key={t}>{t}</option>
                        ))}
                      </select>
                    </td>
                    <td className="schema-values">
                      {a.type === "date" ? (
                        <select
                          aria-label={`Attribute ${i + 1} date pattern`}
                          value={a.date_format || ""}
                          onChange={(e) =>
                            edit(i, { date_format: e.target.value || null })
                          }
                        >
                          <option value="">Detect from data</option>
                          {[
                            "yyyy-MM-dd",
                            "yyyy-MM-dd'T'HH:mm:ss",
                            "yyyy-MM-dd HH:mm:ss",
                            "yyyy-MM-dd'T'HH:mm:ss.SSS",
                            "yyyy-MM-dd'T'HH:mm:ssXXX",
                            "MM/dd/yyyy",
                            "dd/MM/yyyy",
                          ].map((f) => (
                            <option key={f}>{f}</option>
                          ))}
                        </select>
                      ) : a.type === "nominal" ? (
                        a.values.length ? (
                          a.values.join(", ")
                        ) : (
                          "Enumerated from the dataset on conversion"
                        )
                      ) : a.type === "numeric" ? (
                        "All non-missing values must be numeric"
                      ) : (
                        "Text values preserved"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details>
            <summary>View input preview · first 20 instances</summary>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {attributes.map((a, i) => (
                      <th key={i}>{a.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {upload.rows.map((r, i) => (
                    <tr key={i}>
                      {r.map((v, j) => (
                        <td key={j}>
                          {v ?? <span className="muted">missing</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <div className="panel-actions">
            <span className="muted">
              Every override is validated against the full dataset.
            </span>
            <button
              className="button"
              disabled={busy || attributes.some((a) => !a.name.trim())}
              onClick={convert}
            >
              {busy
                ? "Converting…"
                : `Convert to ${upload.target_format.toUpperCase()}`}
              <ArrowRight size={17} />
            </button>
          </div>
        </section>
      )}
      {result && (
        <section className="panel result-panel">
          <div className="panel-heading">
            <h2>
              03 <span>Your converted file is ready</span>
            </h2>
            <span className="badge">
              <Check size={13} />
              Completed
            </span>
          </div>
          <p className="muted">
            {result.download_name} · {result.instance_count} instances ·{" "}
            {result.attribute_count} attributes
          </p>
          <pre>{result.preview}</pre>
          <div className="panel-actions">
            <span className="muted">
              Full header and up to 20 output rows shown.
            </span>
            <button
              className="button"
              onClick={() =>
                download(result.id, result.download_name).catch(setError)
              }
            >
              <Download size={17} />
              Download {result.target_format.toUpperCase()}
            </button>
          </div>
        </section>
      )}
    </>
  );
}
