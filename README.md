# Classroom AI Chat & Skills Assessment Module

This is a standalone, self-contained AI Chat and Skills Assessment module extracted from the Classroom Analytics Platform. It is designed to be committed to its own GitHub repository and hosted on **Render** (as a single unified web service).

---

## Key Features

- **Double-Agent CrewAI Pipeline**: Integrates a Trade Subject Matter Expert and Trainee Competency Assessor.
- **Dynamic Length & Numeric Constraints**: Automatically respects explicit trainee requests (e.g., "in three lines", "in two sentences", "concise").
- **Offline Heuristic Fallback**: Continues working seamlessly using locally pre-defined vocabulary mappings and answers if the API key or Internet connection fails.
- **MongoDB & In-Memory Fallback Storage**: Connects to MongoDB when available (with auto-seeding for trainees), and falls back automatically to safe in-memory storage if MongoDB is not present.
- **Single-Service Render Deployment**: Built to serve compiled React assets directly from FastAPI, letting you host the entire project on Render's free tier as a single service.

---

## Project Structure

```text
standalone_ai_chat/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── chat_llm.py     # CrewAI LLM assessment service
│   │   ├── config.py       # Pydantic Settings loader
│   │   ├── database.py     # MongoDB manager with in-memory fallback
│   │   └── main.py         # FastAPI API endpoints & static serving
│   ├── .env.example
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.jsx         # Standalone chat & stats React view
    │   ├── index.css       # Tailwind CSS styles & animations
    │   └── main.jsx        # App mounting
    ├── index.html
    ├── package.json        # Frontend Node dependencies
    ├── postcss.config.js
    ├── tailwind.config.js
    └── vite.config.js
```

---

## Local Setup

### 1. Run the Backend

1. Navigate to the backend folder:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your `.env` file from the example:
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and fill in your details:
   - `OPENROUTER_API_KEY`: Your OpenRouter API Key (to use Gemini). If left blank, it falls back to the local Ollama Qwen model, or offline heuristics.
   - `OPENROUTER_MODEL`: Model identifier (defaults to `google/gemini-2.5-flash`).
   - `MONGODB_URL`: (Optional) MongoDB connection string. If omitted, the app will store analyses in-memory.

4. Start the FastAPI server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
   ```

---

### 2. Run the Frontend

1. Navigate to the frontend folder:
   ```bash
   cd ../frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open the browser at `http://localhost:5173`. Any API calls to `/api/...` will automatically proxy to the FastAPI backend running on port 8001.

---

## Deploying on Render (Unified Single Service)

You can host both the frontend and backend together on Render for free.

1. Push this `standalone_ai_chat` directory (or its contents) to your GitHub repository.
2. In the Render Dashboard, click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Set the following configurations:
   - **Name**: `classroom-ai-chat`
   - **Language**: `Python`
   - **Branch**: `main`
   - **Build Command**:
     ```bash
     cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
5. Click **Advanced** and add your Environment Variables:
   - `OPENROUTER_API_KEY`: Your OpenRouter Key.
   - `OPENROUTER_MODEL`: `google/gemini-2.5-flash`
   - `MONGODB_URL`: (Optional) A MongoDB connection string (e.g. from MongoDB Atlas).

When the build completes, Render will spin up the FastAPI backend and compile the React static files. FastAPI will serve the React user interface on the root path `/` and expose the API endpoints on `/api/...`, allowing the entire app to run on a single Render instance.

---

## Keeping the Free Instance Awake (24/7 Online)

Render's **Free Tier** web services automatically go to sleep (spin down) after 15 minutes of inactivity. When a new request arrives, it takes 30-50 seconds to boot up again.

To keep your service online and awake 24/7 for free, you can set up a free external ping monitor:

### Option A: Use UptimeRobot (Free & Recommended)
1. Go to [UptimeRobot](https://uptimerobot.com/) and create a free account.
2. Click **Add New Monitor**.
3. Select **Monitor Type**: `HTTP(s)`.
4. Fill in the configurations:
   - **Friendly Name**: `Classroom AI Chat`
   - **URL (or IP)**: Paste your public Render web service URL (e.g., `https://classroom-ai-chat.onrender.com/`).
   - **Monitoring Interval**: Every `5 minutes` or `10 minutes` (well within the 15-minute timeout window).
5. Click **Create Monitor**.

UptimeRobot will ping your Render URL every few minutes, preventing the server from entering sleep mode.

### Option B: Upgrade to Render Starter Tier
If you do not want to use an external ping service, you can upgrade your web service instance type from **Free** to **Starter** ($7/month) in your Render dashboard settings. Starter instances never spin down or go to sleep.

