// src/components/LoadingSpinner.js
function LoadingSpinner() {
  return (
    <div className="spinner-container">
      <div className="spinner"></div>
      <p>ClinicalScout is analyzing trials for you. This may take 30 to 60 seconds.</p>
    </div>
  );
}

export default LoadingSpinner;