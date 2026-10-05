import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeftRight,
  FileSpreadsheet,
  Braces,
  ShieldCheck,
  SlidersHorizontal,
  History,
} from "lucide-react";
import { participants } from "../components";

export default function Landing() {
  return (
    <main className="landing">
      <section className="academic-strip">
        <div>
          <b>Software Engineering - IT303</b>
          <span>Department of Information Technology · NITK, Surathkal</span>
        </div>
        <div className="team">
          <small>PROJECT PARTICIPANTS</small>
          <span>{participants.join(" · ")}</span>
        </div>
      </section>
      <section className="hero">
        <div className="hero-copy">
          <span className="pill">A DATA PREPARATION WORKSPACE</span>
          <h1>
            File Converter
            <br />
            <em>System.</em>
          </h1>
          <p className="hero-subtitle">
            From CSV to ARFF.
            <br />
            And back, with confidence.
          </p>
          <p className="muted">
            Prepare datasets for the WEKA workbench. Review your attributes,
            control the conversion, and keep a clear history of your work.
          </p>
          <div className="hero-actions">
            <Link className="button" to="/register">
              Get started <ArrowRight size={18} />
            </Link>
            <Link className="text-link" to="/login">
              Sign in to your account ↗
            </Link>
          </div>
          <div className="hero-proof">
            <ShieldCheck size={16} /> Authenticated access <span /> Private
            datasets <span /> Both directions
          </div>
        </div>
        <div
          className="conversion-illustration"
          aria-label="CSV dataset converted into ARFF with a reviewed schema"
        >
          <div className="illustration-top">
            <span className="dot" /> THE CONVERSION WORKSPACE{" "}
            <span>01 — 03</span>
          </div>
          <div className="format-flow">
            <div>
              <FileSpreadsheet size={30} />
              <b>.csv</b>
              <small>Tabular data</small>
            </div>
            <span className="flow-arrow">
              <ArrowLeftRight size={26} />
            </span>
            <div>
              <Braces size={30} />
              <b>.arff</b>
              <small>WEKA ready</small>
            </div>
          </div>
          <div className="mock-schema">
            <div className="mock-schema-title">
              <b>Schema review</b>
              <span className="badge">3 attributes</span>
            </div>
            <div className="mock-row">
              <small>ATTRIBUTE</small>
              <small>DETECTED TYPE</small>
            </div>
            <div className="mock-row">
              <span>sepal_length</span>
              <code>numeric</code>
            </div>
            <div className="mock-row">
              <span>species</span>
              <code>nominal</code>
            </div>
            <div className="mock-row">
              <span>observed_on</span>
              <code>date</code>
            </div>
          </div>
          <div className="illustration-bottom">
            <ShieldCheck size={17} />
            <span>Review first. Convert with clarity.</span>
          </div>
        </div>
      </section>
      <section className="feature-section" id="workflow">
        <div className="section-heading">
          <span className="eyebrow">A SIMPLE, TRACEABLE WORKFLOW</span>
          <h2>Your dataset. Three clear steps.</h2>
          <p className="muted">
            Built for students, researchers, and data analysts working with CSV
            and ARFF.
          </p>
        </div>
        <div className="feature-grid">
          {[
            [
              FileSpreadsheet,
              "01",
              "Upload & configure",
              "Choose a CSV or ARFF file. Set the CSV delimiter, quote character, header row, and relation name.",
            ],
            [
              SlidersHorizontal,
              "02",
              "Review your schema",
              "Inspect numeric, nominal, date, and string attributes. Rename columns or correct their types before conversion.",
            ],
            [
              History,
              "03",
              "Convert & download",
              "Preview the generated file, download it securely, and revisit your personal conversion history.",
            ],
          ].map(([Icon, n, title, description]) => (
            <article key={n}>
              <div className="feature-top">
                <Icon size={24} />
                <span>{n}</span>
              </div>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="landing-note">
        <ShieldCheck size={24} />
        <div>
          <h3>Made for a focused data workflow</h3>
          <p>
            Registered users manage their datasets. Administrators manage
            accounts, monitor activity, and configure system limits. Sparse ARFF
            and model training are outside this project's scope.
          </p>
        </div>
        <Link className="text-link" to="/login">
          Open workspace <ArrowRight size={17} />
        </Link>
      </section>
    </main>
  );
}
