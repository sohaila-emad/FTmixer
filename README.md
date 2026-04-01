# FTmixer

Part A-focused implementation for Task 3 Fourier Transform Mixer.

## Scope
- Implemented: Task 3 Part A (FT Magnitude/Phase Mixer parity sprint).
- Not implemented in this sprint: Task 3 Part B (FT properties emphasizer).

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



