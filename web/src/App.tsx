import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import ThemeStrategy from './pages/ThemeStrategy';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ThemeStrategy />} />
        <Route path="*" element={<ThemeStrategy />} />
      </Routes>
    </Router>
  );
}

export default App;
