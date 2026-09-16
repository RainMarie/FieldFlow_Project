import os
import sys
import time
import subprocess
import webbrowser

# Resolve the absolute path to the project root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define target entry points and their execution modes
APPS = [
    {
        "name": "Admin Control Tower",
        "script": os.path.join(ROOT_DIR, "src", "frontend", "admin_dashboard.py"),
        "is_web": False
    },
    {
        "name": "Mobile Field Suite",
        "script": os.path.join(ROOT_DIR, "src", "frontend", "mobile_suite.py"),
        "is_web": True,
        "port": "8551",
        "url": "http://localhost:8551"
    },
    {
        "name": "Sidecar Review Portal",
        "script": os.path.join(ROOT_DIR, "src", "frontend", "sidecar_portal.py"),
        "is_web": False
    }
]

def launch_fieldflow_suite():
    processes = []
    print("=" * 60)
    print("🚀 LAUNCHING FIELDFLOW INTEGRATED SUITE")
    print("=" * 60)

    # 1. Iterate and spawn each application subprocess
    for app in APPS:
        script_path = app["script"]
        if os.path.exists(script_path):
            # Copy current system environment variables
            env = os.environ.copy()
            env["PYTHONPATH"] = ROOT_DIR

            if app.get("is_web"):
                print(f"⚡ Starting {app['name']} as Web App on {app['url']}...")
                env["FLET_SERVER_PORT"] = app["port"]
                env["FLET_VIEW"] = "web_browser"

                p = subprocess.Popen([sys.executable, script_path], env=env)
                processes.append(p)

                # Brief delay to allow port binding before opening browser
                time.sleep(1.5)
                webbrowser.open(app["url"])
            else:
                print(f"🖥️ Starting {app['name']} as Native Desktop Window...")
                p = subprocess.Popen([sys.executable, script_path], env=env)
                processes.append(p)
        else:
            print(f"❌ Error: Could not find target script at: {script_path}")

    print("\n✅ All FieldFlow services launched!")
    print("Press CTRL+C in this terminal to stop all servers safely.")
    print("=" * 60)

    # 2. Keep master process alive to manage background sub-process lifecycles
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down FieldFlow services...")
        for p in processes:
            p.terminate()
        print("🎉 All servers stopped safely.")

if __name__ == "__main__":
    launch_fieldflow_suite()