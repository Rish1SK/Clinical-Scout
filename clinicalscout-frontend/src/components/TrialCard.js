import { useState } from "react";
import ReactMarkdown from "react-markdown";
 
function TrialCard({ trial, index }) {
  const [expanded, setExpanded] = useState(false);
 
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
          {trial.justification.replace(/[#*_`]/g, "").slice(0, 200)}...
        </div>
      )}
 
      {expanded && (
        <div className="trial-full">
          <ReactMarkdown>{trial.justification}</ReactMarkdown>
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
 