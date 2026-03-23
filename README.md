# Cost Calculator Application

A full-stack application for calculating detailed billing costs from uploaded CSV datasets. Built with a pristine **Vanilla JS/CSS/HTML Frontend** (ready for Vercel) and a robust **FastAPI Backend** (ready for Railway).

## Separation of Concerns
- `/frontend`: Modern dynamic web UI with glassmorphism to interact with the API. 
- `/backend`: Python API using Pandas for rigorous dataframe curation. Uses `decimal.Decimal` loaded from strings to prevent floating-point drifts.

## Local Environment Setup

### 1. Running the Backend
Requires Python 3.9+.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
The API will run on `http://127.0.0.1:8000`.

### 2. Running the Frontend
Open another terminal:

```bash
cd frontend
# You can use any static server or Python's built-in http.server
python -m http.server 3000
```
Visit `http://localhost:3000` in your browser. Upload your `.csv`!

## Deployment

### Frontend (Vercel)
1. Add your repository to Vercel.
2. Ensure the "Root Directory" is set to `frontend`.
3. Deploy! Before deploying to production, modify `API_URL` in `frontend/script.js` to point to your Railway domain.

### Backend (Railway)
1. Create a new project on Railway and link your repository.
2. Configure the "Root Directory" to `backend`.
3. Railway will auto-detect the `requirements.txt` and launch using FastAPI/Uvicorn.

## Running Unit Tests (Backend)
```bash
cd backend
pytest
```
