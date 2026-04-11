import React from "react";
import { TransformControlPanel } from "../components/transformExplorer/TransformControlPanel";
import { TransformExplorerProvider } from "../components/transformExplorer/TransformExplorerContext";
import { TransformGuidePanel } from "../components/transformExplorer/TransformGuidePanel";
import { TransformViewport } from "../components/transformExplorer/TransformViewport";
import "../styles/TransformExplorerPage.css";

export function TransformExplorerPage() {
  return (
    <TransformExplorerProvider>
      <div className="transform-shell">
        <aside className="left-panel">
          <h1>Transform Explorer</h1>
          <TransformControlPanel />
        </aside>

        <main className="right-panel">
          <section className="transform-grid">
            <TransformViewport viewportKey="spatial_original" title="Spatial Original" />
            <TransformViewport viewportKey="spatial_transformed" title="Spatial Transformed" />
            <TransformViewport viewportKey="frequency_original" title="Frequency Original" />
            <TransformViewport viewportKey="frequency_transformed" title="Frequency Transformed" />
          </section>

          <TransformGuidePanel />
        </main>
      </div>
    </TransformExplorerProvider>
  );
}
