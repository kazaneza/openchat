import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Upload from './pages/Upload';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/settings" element={<div className="text-center py-16"><h2 className="text-2xl font-bold text-gray-900">Settings</h2><p className="text-gray-600">Settings page coming soon...</p></div>} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;