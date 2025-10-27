# Quick start — super simple (for humans and kids)

This file tells you how to run the Zero Trust app on your computer in the easiest possible way.

Follow these steps exactly. You only need one terminal window.

1) Open a terminal

2) Go to the project folder

```bash
cd /home/gebin/Desktop/ZeroTrustArch-DTSandAI
```

3) Make the start script runnable (only needed once)

```bash
chmod +x ./start.sh
```

4) Start everything (backend + frontend)

```bash
./start.sh
```

Wait a little bit. The script prints messages. When you see a line like:

  Zero Trust Architecture System is ready!

the app is running.

5) Open the app in your web browser

Go to: http://localhost:3000

If that page doesn't load, try refreshing the page after a few seconds.

6) Stop the app (when you are done)

```bash
./stop.sh
```

or (if that does not work) kill the processes shown in the output from the start script, for example:

```bash
# example shown earlier; replace numbers with real ones you see
kill 1445297 1445460
```

Troubleshooting (simple)

- If start fails because a port is busy, it will say "Port 8000 is already in use" or "Port 3000 is already in use". Run this to see what's using it:

```bash
lsof -i :8000 -sTCP:LISTEN -P -n
lsof -i :3000 -sTCP:LISTEN -P -n
```

Then stop that process (use the PID number from the command above):

```bash
kill <PID>
```

- If the frontend shows a red "Connection Error" message, open the browser Developer Tools (usually F12) and check the Network tab for the request to `/api/admin/system_status`. It should show a request going to `http://localhost:8000/api/admin/system_status` and returning JSON. If it returns 404 or 500, check backend logs.

How to read logs (quick):

```bash
# show last lines and keep following (press Ctrl+C to stop)
tail -f logs/backend.log
tail -f logs/frontend.log
```

If backend endpoints are not responding you can check the health endpoint directly:

```bash
curl http://localhost:8000/health
```

If you want to run pieces manually (advanced, optional)

- Start backend only (in case you prefer manual steps):

```bash
cd backend
# create virtual environment (if not created)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# then run the API server in the backend folder
uvicorn main:app --host 0.0.0.0 --port 8000
```

- Start frontend only (in case you prefer manual steps):

```bash
cd frontend
npm install
npm run dev
```

Prerequisites (things you need installed on your computer)

- Python 3 (the script uses `python3` and creates a `venv` inside `backend/`)
- Node.js and npm (to run the frontend)

If those are missing, install them using your package manager (or ask me and I will give commands for your OS).

If something goes wrong, copy the last 50 lines of `logs/backend.log` or `logs/frontend.log` and paste them here, and I'll help fix it.

Have fun testing! If you want, I can also make a screenshot guide or a one-click script for your system. Tell me which you prefer.
