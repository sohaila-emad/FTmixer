import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { MixerPage } from "./pages/MixerPage";

export default function App() {
  return (
    <Routes>
      <Route path="/mixer" element={<MixerPage />} />
      <Route path="*" element={<Navigate to="/mixer" replace />} />
    </Routes>
  );
}
