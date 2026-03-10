# Cloud Optimization Advisor

An AI-powered Cloud Resource Intelligence Advisor application. It analyzes cloud deployment environments, flags underutilized and high-risk resources, and provides actionable optimization insights including specific remediation scripts (CLI and Terraform) to minimize cloud waste and improve efficiency.

This repository features a complete end-to-end setup including a **Vite + React Frontend** and a **Node.js + Express Backend** seamlessly integrated with the **Google Gemini Pro SDK**.

---

## 🚀 Features
- **AI-Powered Diagnostics:** Leverages the Gemini 2.5 Flash model as the core reasoning engine behind "ARIA" (AI Resource Intelligence Advisor) to scrutinize cloud architecture and deliver tailored optimization strategies.
- **Multi-Cloud Integration:** Emulates parsing of data dumps/CSVs originating from top public cloud providers including AWS, Google Cloud (GCP), and Azure.
- **Real-Time Data Visualization:** Uses React Recharts to draw comprehensive data analytics describing CPU/Memory utilization, risk indices, regional costs, and projected savings.
- **Copy-Paste Remediations:** Instantly generates precise AWS CLI commands and HashiCorp Terraform configuration snippets mapping to its actionable insights.
- **Responsive & Futuristic UI:** Implements a cutting-edge dark mode interface inspired by modern cyber/hacking dashboards, leveraging glassmorphism and animated components to deliver premium UX.

---

## 🛠 Tech Stack

### Frontend
- **Framework:** React 18, Vite
- **Styling:** CSS3 variables & Flex/Grid configurations for responsive dark-mode styling
- **Charts:** [Recharts](https://recharts.org/) for rendering comprehensive multi-axis analytic visualizations
- **Icons:** [Lucide-React](https://lucide.dev/) for crisp, scalable iconography

### Backend
- **Runtime:** Node.js, Express.js
- **AI Integration:** `@google/genai` (Gemini model orchestration for conversational intelligence)
- **Environment:** `dotenv` for handling secure secrets (e.g. `GEMINI_API_KEY`)

---

## 📂 Project Structure

```text
/
├── frontend/             # The Vite/React application
│   ├── src/              # React components and styling
│   ├── public/           # Static assets
│   ├── vite.config.js    # Vite tooling & Proxy configs
│   └── package.json      # Frontend dependencies & scripts
│
├── backend/              # Node.js/Express.js Server
│   ├── server.js         # Core endpoint implementations
│   ├── .env              # Secrets and runtime flags (NOT COMMITTED)
│   └── package.json      # Backend dependencies & scripts
│
├── .gitignore            # Global gitignore configuration
└── README.md             # This global documentation file
```

---

## ⚙️ Setup and Installation

### Prerequisites
- [Node.js](https://nodejs.org/) (v16.x or newer strongly recommended)
- [NPM](https://www.npmjs.com/) or Yarn package manager
- A valid Google Gemini API Key. You can get yours from the [Google AI Studio](https://aistudio.google.com/app/apikey).

### 1. Clone & Bootstrap the Environment

First, open your terminal and install dependencies for both the frontend and backend contexts:

```bash
# Install backend dependencies
cd backend
npm install

# Return to root, then install frontend dependencies
cd ../frontend
npm install
```

### 2. Configure Environment Variables

The backend relies on Google Gemini for the chat advisor functionality.

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Open the `.env` file (or duplicate `.env.example` if it exists) in `backend/.env`.
3. Set your valid API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   PORT=3000
   ```

### 3. Run the Development Servers

You will want to launch both the backend server and frontend development server concurrently to ensure smooth proxying for API hits.

**Terminal 1 (Backend API Server):**
```bash
cd backend
npm start
```

**Terminal 2 (Frontend Client Server):**
```bash
cd frontend
npm run dev
```

The application will now safely boot up locally! Navigate your browser to `http://localhost:5173`. Any API queries directed at `/api/*` seamlessly proxy through to your local Node server living at `http://localhost:3000`.

---

## 💡 How To Use
1. Upon loading `http://localhost:5173`, click **Load Demo: 10 Real-World VMs** to populate the state machine with simulated data.
2. Analyze the newly populated diagnostic metrics available in the **Overview** dashboard (Radar charts, Resource breakdowns, Heatmaps).
3. Access the **AI Advisor** tab to interact directly with ARIA. Try asking: *"Show me the ROI if I apply all your recommended remediations."* or *"What is my biggest architecture risk right now?"*

---

## 🚀 Deployment (Vercel)
This app is fully optimized for **zero-config deployment on Vercel**. 
Because it includes a `vercel.json` file, Vercel understands how to automatically build the Vite React app and configure the Express server via Serverless functions automatically.

1. Create a new project on Vercel and import this repository.
2. Vercel will automatically read `vercel.json` and build the UI correctly while routing all `/api/*` traffic to the backend API.
3. Add `GEMINI_API_KEY` to your Vercel Project Environment Variables.

---

## 🤝 Contributing
Contributions are always welcome! If you'd like to improve the UI logic, add additional charts, refine prompt injection engineering on the backend API, or simply resolve a bug, feel free to open a Pull Request.

---

*Powered by Google Gemini* ✨
