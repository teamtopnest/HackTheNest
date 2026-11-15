import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Acquisition from './pages/Acquisition';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/acquisition/*" element={<Acquisition />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App