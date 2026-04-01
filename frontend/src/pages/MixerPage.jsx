import React from "react";
import { ComponentViewer } from "../components/mixer/ComponentViewer";
import { ControlPanel } from "../components/mixer/ControlPanel";
import { ImageMixerProvider } from "../components/mixer/ImageMixerContext";
import { ImageViewer } from "../components/mixer/ImageViewer";
import { OutputViewer } from "../components/mixer/OutputViewer";
import "../styles/MixerPage.css";

export function MixerPage() {
  const viewerIndexes = [0, 1, 2, 3];

  return (
    <ImageMixerProvider>
      <div className="mixer-shell">
        <aside className="left-panel">
          <h1>Frequency Blend Studio</h1>
          <ControlPanel />
        </aside>

        <main className="right-panel">
          <section className="viewer-grid">
            {viewerIndexes.map((idx) => (
              <ImageViewer key={`image-${idx}`} index={idx} />
            ))}
          </section>

          <section className="viewer-grid">
            {viewerIndexes.map((idx) => (
              <ComponentViewer key={`component-${idx}`} index={idx} />
            ))}
          </section>

          <section className="output-grid">
            <OutputViewer index={0} />
            <OutputViewer index={1} />
          </section>
        </main>
      </div>
    </ImageMixerProvider>
  );
}
