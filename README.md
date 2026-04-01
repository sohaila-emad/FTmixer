# FTmixer

Task 3 implementation with both Part A mixer and Part B transform explorer modes.

## Scope
- Implemented: Task 3 Part A (FT Magnitude/Phase Mixer).
- Implemented: Task 3 Part B (transform explorer) in a separate mode inside the same app.

## Project Layout
- Backend: Django + DRF in backend
- Frontend: React + Vite in frontend
- Local reference source used for parity checks: reference code

## Run (Windows)

Backend:
1. Open terminal in backend
2. Install dependencies:
	- pip install -r requirements.txt
3. Apply migrations:
	- python manage.py migrate
4. Run server:
	- python manage.py runserver

Frontend:
1. Open terminal in frontend
2. Install dependencies:
	- npm install
3. Run dev server:
	- npm run dev
4. Open app at:
	- http://localhost:5173/mixer
	- switch to Part B from the top mode switch bar (Transform Explorer)

## Current Part A Status
- 4 input image viewers with per-view double-click replace.
- Color input handling converted to grayscale on backend.
- Unified image sizing to smallest loaded dimensions for mixing.
- Per-view FT component display selector (magnitude/phase/real/imaginary).
- Two output routing targets supported.
- Brightness/contrast drag enabled for input views and FT views.
- Weighted mixing for magnitude/phase and real/imaginary modes.
- Shared FT ROI rectangle with drag/resize handles and visual inner/outer highlighting.
- Progress updates during async mixing.
- Rapid retrigger cancellation hardened to prevent stale worker overwrite.

## Verification Baseline
- Backend: python manage.py check passes.
- Frontend: npm run build passes.
- Controller smoke checks:
  - rapid retrigger routes result to latest output only
  - no-image early mix request exits cleanly without crash

## Part B Highlights
- Same app mode switch between Part A and Part B.
- Four synchronized Part B viewports:
	- spatial original
	- spatial transformed
	- frequency original
	- frequency transformed
- Operation registry-backed action system with dynamic parameter schema.
- Domain toggle: apply in spatial or frequency domain with synchronized paired-domain updates.
- Supported actions:
	- shift
	- complex exponential multiply
	- stretch (fractional/integer)
	- mirror/symmetry duplication
	- even/odd construction
	- rotate (0..360, auto-fit canvas)
	- differentiate
	- integrate
	- window multiply (rectangular, gaussian, hamming, hanning)
	- repeated Fourier (standalone and repeat overlay)
- Part B async apply flow includes cancellation safeguards and stale-response protection.

## Part B Verification Snapshot
- Full action matrix executed for both domains:
	- 10 operations x 2 domains = 20 apply pairs passed.
- Rotation auto-fit validation passed.
- Window type validations passed for all 4 window modes.
- Repeat Fourier overlay validation passed.



