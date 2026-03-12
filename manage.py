import subprocess
import time
import sys

def run(cmd):
    subprocess.check_call(cmd)

def install():
    
    # Install Python dependencies
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def db():
    
    # Start database containers
    if subprocess.run(["docker", "start", "mongo-milano"], capture_output=True).returncode != 0:
        run(["docker", "run", "-d", "-p", "27017:27017", "--name", "mongo-milano", "mongo"])
    
    if subprocess.run(["docker", "start", "neo4j-milano"], capture_output=True).returncode != 0:
        run(["docker", "run", "-d", "-p", "7474:7474", "-p", "7687:7687", "--name", "neo4j-milano", "-e", "NEO4J_AUTH=none", "neo4j"])

def stop():
    
    # Stop database containers
    subprocess.run(["docker", "stop", "mongo-milano", "neo4j-milano"])

def seed():
    
    # Run data seeding script
    run([sys.executable, "main.py"])

def app():
    
    # Launch Streamlit application
    run([sys.executable, "-m", "streamlit", "run", "app.py"])

def run_all():
    
    # Execute complete setup workflow
    db()
    time.sleep(5) 
    install()
    seed()
    app()

if __name__ == "__main__":
    commands = {"install": install, "db": db, "stop": stop, "seed": seed, "app": app, "run": run_all}
    
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Usage: python manage.py [install|db|stop|seed|app|run]")
        sys.exit(1)
    
    commands[sys.argv[1]]()