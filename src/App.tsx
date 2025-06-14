import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Hero from './components/Hero';
import Services from './components/Services';
import CaseStudies from './components/CaseStudies';
import Testimonials from './components/Testimonials';
import Team from './components/Team';
import Contact from './components/Contact';
import Footer from './components/Footer';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';
import ForgotPassword from './components/auth/ForgotPassword';
import VerifyPhone from './components/auth/VerifyPhone';
import Dashboard from './components/dashboard/Dashboard';
import { useAuth } from './hooks/useAuth';

function App() {
  useEffect(() => {
    document.title = 'Agile Partners AI | Intelligent Solutions for Business';
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route path="/register" element={<RegisterForm />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/verify-phone" element={<VerifyPhone />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-white dark:bg-gray-900">
              <Header />
              <main>
                <Hero />
                <Services />
                <CaseStudies />
                <Testimonials />
                <Team />
                <Contact />
              </main>
              <Footer />
            </div>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;