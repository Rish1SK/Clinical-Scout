import { useState } from "react";
import ReactMarkdown from "react-markdown";

function TrialCard({ trial, index }) {
  const [expanded, setExpanded] = useState(false);

  const plainPreview = trial.justification
    .replace(/#{1,6}\s/g, "")
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/`/g, "")
    .replace(/---/g, "")
    .slice(0, 200);

  return (
    <div className="trial-card">

      <div className="trial-header">
        <div className="trial-meta">
          <span className="trial-rank">#{index}</span>
          <span className="trial-id">{trial.nct_id}</span>
        </div>
        <h3 className="trial-title">{trial.title}</h3>
        <a
          className="registry-link"
          href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
          target="_blank"
          rel="noreferrer"
        >
          View on ClinicalTrials.gov →
        </a>
      </div>

      {!expanded && (
        <div className="trial-preview">
          {plainPreview}...
        </div>
      )}

      {expanded && (
        <div className="trial-full">
          <ReactMarkdown
            components={{
              h3: ({node, ...props}) => (
                <h3 style={{
                  color: "#0f3460",
                  borderBottom: "1px solid #eee",
                  paddingBottom: "0.3rem",
                  margin: "1.2rem 0 0.5rem",
                  fontSize: "0.95rem"
                }} {...props} />
              ),
              strong: ({node, ...props}) => (
                <strong style={{ color: "#0f3460" }} {...props} />
              ),
              li: ({node, ...props}) => (
                <li style={{
                  lineHeight: "1.7",
                  marginBottom: "0.3rem",
                  fontSize: "0.9rem",
                  wordBreak: "break-word",
                  overflowWrap: "break-word"
                }} {...props} />
              ),
              p: ({node, ...props}) => (
                <p style={{
                  lineHeight: "1.7",
                  marginBottom: "0.6rem",
                  fontSize: "0.9rem",
                  wordBreak: "break-word",
                  overflowWrap: "break-word"
                }} {...props} />
              ),
              hr: ({node, ...props}) => (
                <hr style={{
                  border: "none",
                  borderTop: "1px solid #eee",
                  margin: "1rem 0"
                }} {...props} />
              ),
            }}
          >
            {trial.justification}
          </ReactMarkdown>
        </div>
      )}

      <button
        className="expand-button"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "▲ Collapse Analysis" : "▼ View Full Analysis"}
      </button>

    </div>
  );
}

export default TrialCard;