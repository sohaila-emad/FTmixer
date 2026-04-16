# FTmixer

**A dual-mode Fourier Transform image workbench** — blend images in the frequency domain, and explore how spatial transforms and their frequency-domain counterparts relate to each other.

Built with Django + DRF on the backend and React + Vite on the frontend.

---

## What It Does

FTmixer has two independent modes, switchable via the top navigation bar:

### Part A — Frequency Blend Studio

Load up to four images and mix them together using their **Fourier Transform components**. Instead of blending pixels, you blend magnitudes, phases, real parts, or imaginary parts — letting you reconstruct a hybrid image that inherits structure from one image and texture from another.

<img width="1890" height="1018" alt="Screenshot_16-4-2026_171849_localhost" src="https://github.com/user-attachments/assets/9668bd81-b678-4db2-be66-2cfa5cf26604" />


Key capabilities:
- **4 input image slots** with per-slot double-click replacement
- **FT component viewer** per slot — choose between Magnitude, Phase, Real, or Imaginary display
- **Mixing modes**: Magnitude/Phase or Real/Imaginary
- **Region of Interest (ROI)**: a draggable, resizable rectangle that selects which part of the frequency spectrum to mix (inner or outer region)
- **Per-image region mode**: each slot can independently contribute from the inner or outer ROI region
- **Image sizing policy**: align all images to the Smallest, Largest, or a Fixed resolution before mixing
- **Brightness/contrast drag** on both input viewers and FT viewers
- **Two output slots** — route results to Output 1 or Output 2 independently
- **Async mixing** with progress bar, and stale-response protection against rapid re-triggers
- Optional **FFT bottleneck simulation** to observe async cancellation behavior

### Part B — Transform Explorer

Load a single source image, apply one of ten mathematical operations, and watch the effect propagate across four synchronized viewports:
<img width="1875" height="850" alt="Screenshot_16-4-2026_171923_localhost" src="https://github.com/user-attachments/assets/c822df50-4696-4885-b7c9-8e49e29e3981" />


| Viewport | Shows |
|---|---|
| Spatial Original | The untouched source image |
| Spatial Transformed | Source after the operation in the spatial domain |
| Frequency Original | FFT of the source |
| Frequency Transformed | FFT of the transformed result |

Applying in **Spatial Domain** runs the operation on the image then recomputes its FFT. Applying in **Frequency Domain** runs the operation on the spectrum then reconstructs via IFFT — so you can compare cause and effect in both directions.

**Supported operations:**

| Operation | What it does |
|---|---|
| Shift | Circular shift with wrap-around (np.roll) |
| Complex Exponential Multiply | Multiplies by A · exp(j(ωx·x + ωy·y + φ)) — scales magnitude, creates phase ramps |
| Stretch | Center-referenced scaling on a fixed canvas |
| Mirror / Symmetry Duplication | Flip and concatenate along horizontal, vertical, or both axes |
| Even / Odd Construction | Decomposes signal into even and odd components |
| Rotate | Free rotation (0–360°) with auto-fit canvas expansion |
| Differentiate | Numerical differentiation along x, y, or both |
| Integrate | Cumulative integration |
| Window Multiply | Convolves with Rectangular, Gaussian, Hamming, or Hanning kernels |
| Repeated Fourier | Applies FFT repeatedly (standalone or overlay) |

An **Operation Guide panel** sits below the viewports and shows parameter units, expected spatial/frequency effects, and — for the Complex Exponential — live hints computing frequency shift in bins and ramp period in px/cycle.

---

## Architecture

```
FTmixer/
├── backend/                  # Django + DRF
│   ├── ImageMixer/
│   │   ├── views.py          # REST endpoints (upload, mix, component, sizing…)
│   │   ├── serializers.py    # Request/response validation
│   │   └── services/
│   │       ├── mixer.py      # FFTImageMixer — weighted FT component blending
│   │       ├── controller.py # Request dispatch, async worker, stale-cancel logic
│   │       ├── custom_image.py
│   │       ├── modes_enum.py # ComponentMode, MixMode, RegionMode enums
│   │       └── transform_explorer/
│   │           ├── actions.py          # OperationSpec registry (10 operations)
│   │           ├── controller.py       # Async apply flow
│   │           ├── complex_helpers.py  # rotate, stretch, convolve, repeat FFT
│   │           └── validators.py
│   └── config/               # Django settings, URL root, WSGI
│
└── frontend/                 # React + Vite
    └── src/
        ├── App.jsx            # Top-level router + mode-switch bar
        ├── pages/
        │   ├── MixerPage.jsx
        │   └── TransformExplorerPage.jsx
        ├── components/
        │   ├── mixer/
        │   │   ├── ImageMixerContext.jsx   # Global state + API calls
        │   │   ├── ImageViewer.jsx         # Input slot with drag brightness/contrast
        │   │   ├── ComponentViewer.jsx     # FT display with ROI drag/resize handles
        │   │   ├── ControlPanel.jsx        # Sidebar controls
        │   │   ├── OutputViewer.jsx        # Result display
        │   │   └── MixerProgressBar.jsx
        │   └── transformExplorer/
        │       ├── TransformExplorerContext.jsx
        │       ├── TransformControlPanel.jsx
        │       ├── TransformViewport.jsx
        │       └── TransformGuidePanel.jsx
        └── styles/
            ├── global.css              # Deep-space color theme (Space Grotesk)
            ├── MixerPage.css
            └── TransformExplorerPage.css
```

**Tech stack:**

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Axios |
| Backend | Django 4.x, Django REST Framework, django-cors-headers |
| Image processing | NumPy, OpenCV (cv2), Pillow |
| Styling | Custom CSS with CSS variables, Space Grotesk font |

---

## Getting Started

> **Platform note:** The run instructions below target Windows. On macOS/Linux the commands are identical except use `python3` instead of `python` if needed.

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
# 1. Enter the backend directory
cd backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Apply migrations (creates local SQLite DB)
python manage.py migrate

# 4. Start the Django dev server
python manage.py runserver
# → Running on http://127.0.0.1:8000
```

**requirements.txt:**
```
Django>=4.2,<5
djangorestframework>=3.14,<4
django-cors-headers>=4.3,<5
numpy>=1.24,<3
opencv-python>=4.8,<5
Pillow>=10,<12
```

### Frontend

```bash
# 1. Enter the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite dev server
npm run dev
# → Running on http://localhost:5173
```

### Open the app

| Mode | URL |
|---|---|
| Part A — Mixer | http://localhost:5173/mixer |
| Part B — Transform Explorer | http://localhost:5173/transform-explorer |

Use the **mode switch bar** at the top to toggle between modes. The two modes are completely independent — you can have a mix in progress in Part A while exploring a transform in Part B.

---

## Usage Walkthrough

### Mixing Images (Part A)

1. Click **"Upload up to 4 images"** in the sidebar to load images into the four input slots. You can also **double-click any individual slot** to replace just that image.
2. Choose a **Mixing Mode**: `Magnitude / Phase` (default) or `Real / Imaginary`.
3. Use the **per-image weight sliders** (0–100%) and **component mode selectors** to decide what each image contributes. For example: Image 1 contributes Magnitude at 80%, Image 2 contributes Phase at 80%.
4. (Optional) Switch **Region Mode** to `Inner / Outer` to restrict mixing to the low-frequency center or the high-frequency periphery of the spectrum. Drag the **cyan ROI rectangle** in any ComponentViewer to reposition it, or resize it from the handles.
5. Choose which **Output Port** (1 or 2) will receive the result.
6. Click **"Start Mix"**. A progress bar tracks the async operation. Clicking again while mixing cancels the current run and starts fresh.

### Exploring Transforms (Part B)

1. Click **"Upload Source Image"** to load your starting image.
2. Select an **Operation** from the dropdown (e.g., "Shift", "Rotate", "Window Multiply").
3. Choose **Apply Domain** — Spatial or Frequency.
4. Adjust the **operation parameters** (shift amount, rotation angle, scale factors, window type, etc.).
5. Click **"Apply Operation"**. All four viewports update simultaneously.
6. Read the **Operation Guide panel** below the viewports to understand what you're seeing — it shows expected behavior for both domain directions, parameter units, and (for Complex Exponential) live computed hints.

---

## API Reference

The backend exposes a REST API under `/api/mixer/`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/mixer/upload/` | Upload a single image to a slot (0–3) |
| `POST` | `/api/mixer/mix/` | Trigger an async mix; returns a task ID |
| `GET` | `/api/mixer/mix/<task_id>/progress/` | Poll mixing progress (0–100%) |
| `GET` | `/api/mixer/mix/<task_id>/result/` | Retrieve the mixed output image |
| `POST` | `/api/mixer/component/` | Fetch an FT component view for a slot |
| `POST` | `/api/mixer/brightness/` | Adjust brightness/contrast on a viewer |
| `POST` | `/api/mixer/sizing/` | Apply image sizing policy across all loaded images |
| `POST` | `/api/transform/upload/` | Upload source for Transform Explorer |
| `POST` | `/api/transform/apply/` | Apply an operation; returns task ID |
| `GET` | `/api/transform/apply/<task_id>/progress/` | Poll transform progress |
| `GET` | `/api/transform/apply/<task_id>/result/` | Retrieve the four viewport images |
| `GET` | `/api/transform/operations/` | List all available operations with parameter schemas |

---

## Design Details

### Color Theme

The UI uses a **deep-space aesthetic** — a dark navy background with radial gradient lighting in cyan (`#16f4d0`), blue (`#22b6ff`), and amber (`#ff8f45`). The font is [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk).

CSS custom properties driving the theme:

```css
--bg-deep: #0b1222;
--bg-mid:  #13263f;
--accent-a: #16f4d0;   /* teal — active elements */
--accent-b: #22b6ff;   /* blue — info / FT */
--accent-c: #ff8f45;   /* amber — outputs / warnings */
```

### Async Cancellation

Both Part A and Part B use a **request ID counter** pattern: each new mix or apply increments a counter, and polling callbacks check whether their ID is still current before updating state. This means rapid re-triggers never overwrite results with stale data from a slower earlier request. The backend also supports explicit cancel signals so the worker thread terminates early rather than completing work that will be discarded.

### ROI System

The Region of Interest rectangle is rendered as an SVG overlay on each ComponentViewer. It has **8 drag handles** (corners + midpoints) and a body-drag for reposition. All four ComponentViewers share the same ROI state, so moving it in one slot moves it in all. The inner region is highlighted with a soft teal fill; the outer region darkens — giving a clear visual of which part of the spectrum each slot will contribute.

---

## Verification Snapshot

**Part A:**
- Rapid retrigger routes result to latest output only — stale worker writes are discarded
- No-image early mix request exits cleanly without crash
- `python manage.py check` passes
- `npm run build` passes

**Part B:**
- Full operation matrix: 10 operations × 2 domains = 20 apply pairs passed
- Rotation auto-fit canvas validation passed
- Window type validations passed for all 4 window types (Rectangular, Gaussian, Hamming, Hanning)
- Repeat Fourier overlay validation passed

---

## Project Scope

This project implements **Task 3** of a DSP / image processing curriculum:

- **Part A** — FT Magnitude/Phase Mixer: blend images by mixing their Fourier components in a user-controlled region of the spectrum.
- **Part B** — Transform Explorer: interactively apply spatial/frequency-domain operations and observe the paired-domain response.

A local reference implementation was used for parity checks during development.

---

## License

Academic / coursework project. See repository root for any license terms.
