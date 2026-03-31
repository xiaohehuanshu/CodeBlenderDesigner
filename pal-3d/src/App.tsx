import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { Home } from './pages/Home';
import { Workflow } from './pages/Workflow';
import { Cases } from './pages/Cases';
import { Docs } from './pages/Docs';
import { About } from './pages/About';
import { Explore } from './pages/Explore';
import { Tutorial } from './pages/Tutorial';
import { CaseDetail } from './pages/CaseDetail';
import { Papers } from './pages/Papers';
import { Github } from './pages/Github';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/workflow" element={<Workflow />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="/about" element={<About />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/tutorial" element={<Tutorial />} />
            <Route path="/cases/:id" element={<CaseDetail />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/github" element={<Github />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}
