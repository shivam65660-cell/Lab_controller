# 🛡️ Sentinel Advance V1 - Lab Network Controller

## 📌 Overview

Sentinel Advance V1 is a **Flask-based network lab management and monitoring tool** designed for **educational and internal lab environments**.

It allows administrators to:

* Discover devices in the local network
* Execute remote administrative commands
* Monitor system activity
* Manage files remotely

⚠️ **Disclaimer:** This project is strictly for **educational purposes and controlled lab environments only**. Unauthorized use on networks without permission is illegal.

---

## 🚀 Features

### 🔍 Network Scanning

* Automatic LAN device discovery
* Hostname detection
* Firewall status indication

### 💻 Remote Administration

* Execute commands using PsExec
* Kill processes remotely
* Restart systems
* Send messages to connected machines

### 📊 Monitoring

* Live bandwidth usage
* Task list retrieval
* Real-time console output

### 📁 File Management

* Remote file explorer
* Download files from target machines
* Upload files via admin shares

### 🖼️ Advanced Controls

* Remote screenshot capture
* Enable RDP remotely
* Automated system configuration (lab use)

---

## 🧠 Tech Stack

* Backend: Python (Flask)
* Frontend: HTML, Bootstrap
* Networking: Socket, ARP scanning
* Database: SQLite
* Remote Execution: PsExec

---

## 📂 Project Structure

```
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── screenshots/
│   └── downloads/
├── sentinel_v4.db
├── psexec.exe
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/sentinel-advance.git
cd sentinel-advance
```

### 2️⃣ Install Dependencies

```bash
pip install flask flask-socketio pynput
```

### 3️⃣ Run Application

```bash
python app.py
```

### 4️⃣ Open in Browser

```
http://localhost:5000
```

---

## 🔐 Requirements

* Windows Environment (for PsExec)
* Administrator Access on target machines
* Same Local Network

---

## ⚠️ Important Notes

* Works only in LAN environment
* Requires admin credentials for remote execution
* Firewall may block some features

---

## 🚫 Legal Disclaimer

This tool is intended **only for authorized lab testing and educational purposes**.
The developer is not responsible for misuse.

---

## 👨‍💻 Author

Shivam Patel

---
