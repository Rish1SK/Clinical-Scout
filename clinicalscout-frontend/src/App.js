import { useState } from "react";
import axios from "axios";
import SearchForm from "./components/SearchForm";
import TrialCard from "./components/TrialCard";
import LoadingSpinner from "./components/LoadingSpinner";
import "./App.css";
 
const API_URL = "http://localhost:8000";
 
function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);
  const [totalFound, setTotalFound] = useState(0);
 
  const handleSearch = async (question) => {
    setLoading(true);
    setError(null);
    setSearched(true);
    setResults([]);
    setTotalFound(0);
 
    try {
      const response = await axios.post(`${API_URL}/search`, { question });
      setResults(response.data.trials);
      setTotalFound(response.data.total_found);
    } catch (err) {
      setError("Something went wrong. Please check the API is running and try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
 
  return (
    <div className="app">
      <header className="app-header">
        <h1>ClinicalScout</h1>
        <p>Find the right clinical trial for your situation</p>
      </header>
 
      <main className="app-main">
        <SearchForm onSearch={handleSearch} loading={loading} />
 
        {loading && <LoadingSpinner />}
 
        {error && <p className="error">{error}</p>}
 
        {!loading && searched && results.length === 0 && !error && (
          <p className="no-results">
            No matching trials found. Try broadening your search.
          </p>
        )}
 
        {!loading && results.length > 0 && (
          <section className="results">
            <h2>{totalFound} Matched Trials — Click any card to view full analysis</h2>
            <div className="results-grid">
              {results.map((trial, index) => (
                <TrialCard
                  key={trial.nct_id}
                  trial={trial}
                  index={index + 1}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
 
export default App;
 