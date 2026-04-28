// src/components/SearchForm.js
import { useState } from "react";

function SearchForm({ onSearch, loading }) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (question.trim()) {
      onSearch(question);
    }
  };

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <textarea
        className="search-input"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Describe your situation in plain language. For example: I am a 54-year-old woman with stage III non-small cell lung cancer with an EGFR mutation. I live in Chicago and can travel up to 50 miles. I work weekdays and am available evenings and weekends."
        rows={5}
        disabled={loading}
      />
      <button
        className="search-button"
        type="submit"
        disabled={loading || !question.trim()}
      >
        {loading ? "Searching..." : "Find Matching Trials"}
      </button>
    </form>
  );
}

export default SearchForm;