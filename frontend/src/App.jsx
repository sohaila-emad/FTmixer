import React from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { TransformExplorerPage } from "./pages/TransformExplorerPage";
import { MixerPage } from "./pages/MixerPage";

export default function App() {
  return (
    <div className="app-shell">
      <header className="mode-switch-bar">
        <NavLink to="/mixer" className={({ isActive }) => `mode-switch-link ${isActive ? "active" : ""}`}>
          Fourier Playground
        </NavLink>
        <NavLink
          to="/transform-explorer"
          className={({ isActive }) => `mode-switch-link ${isActive ? "active" : ""}`}
        >
          Transform Explorer
        </NavLink>
      </header>

      <Routes>
        <Route path="/mixer" element={<MixerPage />} />
        <Route path="/transform-explorer" element={<TransformExplorerPage />} />
        <Route path="/emphasizer" element={<Navigate to="/transform-explorer" replace />} />
        <Route path="*" element={<Navigate to="/mixer" replace />} />
      </Routes>
    </div>
  );
}
