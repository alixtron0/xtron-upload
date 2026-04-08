
import os
import json
import urllib.parse
import shutil
import mimetypes
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

# ================= Configuration =================
HOST = '0.0.0.0'
PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')

# In-memory session store: { "session_token": { "id": "user_id", "role": "full" } }
SESSIONS = {}

# Ensure required directories and files exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(USERS_FILE):
    default_users = {
        "xtron_admin_123": {"role": "full"},
        "xtron_view_456": {"role": "view"}
    }
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_users, f, indent=4)
    print(f"[*] Created default users.json. Admin ID: xtron_admin_123")


# ================= Frontend (HTML/CSS/JS) =================
HTML_APP = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xtron Upload Center</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-panel: #1e293b;
            --bg-hover: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --success: #10b981;
            --warning: #f59e0b;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; }
        
        /* Login Screen */
        #login-screen { display: flex; align-items: center; justify-content: center; height: 100vh; width: 100vw; position: fixed; top: 0; left: 0; background: var(--bg-dark); z-index: 1000; }
        .login-box { background: var(--bg-panel); padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; text-align: center; border: 1px solid var(--border); }
        .login-box h1 { margin-bottom: 10px; color: var(--primary); font-size: 24px; }
        .login-box p { color: var(--text-muted); margin-bottom: 25px; font-size: 14px; }
        .input-group { margin-bottom: 20px; }
        
        input[type="text"], select { width: 100%; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-dark); color: var(--text-main); font-size: 16px; outline: none; transition: 0.2s; }
        input[type="text"]:focus, select:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        
        button { background: var(--primary); color: white; border: none; padding: 10px 16px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: 0.2s; display: inline-flex; align-items: center; gap: 8px; outline: none; }
        button:hover { background: var(--primary-hover); }
        button.danger { background: var(--danger); }
        button.danger:hover { background: var(--danger-hover); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* Main App Layout */
        #app-screen { display: none; flex-direction: column; flex: 1; }
        header { background: var(--bg-panel); border-bottom: 1px solid var(--border); padding: 16px 32px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        .brand { font-size: 20px; font-weight: bold; color: var(--primary); display: flex; align-items: center; gap: 10px; }
        
        .header-right { display: flex; align-items: center; gap: 24px; }
        .storage-info { display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
        .storage-text { font-size: 12px; color: var(--text-muted); }
        .storage-text span { font-weight: 600; color: var(--text-main); }
        .storage-bar { width: 160px; height: 6px; background: var(--bg-dark); border-radius: 3px; overflow: hidden; }
        .storage-bar-fill { height: 100%; width: 0%; transition: width 0.5s ease, background-color 0.5s ease; background: var(--success); }
        
        .user-info { display: flex; align-items: center; gap: 16px; font-size: 14px; color: var(--text-muted); border-left: 1px solid var(--border); padding-left: 24px; }
        .role-badge { background: rgba(59, 130, 246, 0.2); color: var(--primary); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        
        main { padding: 32px; flex: 1; max-width: 1200px; margin: 0 auto; width: 100%; position: relative; }
        
        /* Toolbar & Breadcrumbs */
        .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
        .breadcrumbs { display: flex; align-items: center; gap: 8px; font-size: 16px; background: var(--bg-panel); padding: 10px 20px; border-radius: 8px; border: 1px solid var(--border); flex: 1; overflow-x: auto; }
        .breadcrumb-item { cursor: pointer; color: var(--text-muted); transition: 0.2s; white-space: nowrap; }
        .breadcrumb-item:hover { color: var(--primary); }
        .breadcrumb-sep { color: var(--border); }
        .breadcrumb-active { color: var(--text-main); font-weight: 500; }
        .actions { display: flex; gap: 12px; }
        .hidden { display: none !important; }

        /* File List */
        .file-list { background: var(--bg-panel); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; position: relative; }
        .file-row { display: grid; grid-template-columns: auto 1fr auto auto 170px; align-items: center; gap: 16px; padding: 16px 24px; border-bottom: 1px solid var(--border); transition: 0.2s; }
        .file-row:last-child { border-bottom: none; }
        .file-row:hover { background: var(--bg-hover); }
        .file-header { background: rgba(0,0,0,0.2); font-weight: 600; color: var(--text-muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
        .file-row:hover.file-header { background: rgba(0,0,0,0.2); }
        
        .file-icon { width: 24px; height: 24px; color: var(--primary); display: flex; align-items: center; justify-content: center; }
        .file-name { font-weight: 500; cursor: pointer; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-decoration: none; }
        .file-name:hover { text-decoration: underline; color: var(--primary); }
        .file-size, .file-date { color: var(--text-muted); font-size: 14px; white-space: nowrap; }
        .file-actions { display: flex; gap: 4px; justify-content: flex-end; }
        
        .icon-btn { background: transparent; color: var(--text-muted); padding: 6px; border-radius: 6px; border: 1px solid transparent; }
        .icon-btn:hover { background: var(--bg-dark); color: var(--primary); border-color: var(--border); }
        .icon-btn.danger:hover { color: var(--danger); }
        
        /* Empty state */
        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
        .empty-state svg { width: 64px; height: 64px; margin-bottom: 16px; opacity: 0.5; }

        /* Modals */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.7); z-index: 2000; display: none; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
        .modal { background: var(--bg-panel); padding: 30px; border-radius: 12px; width: 100%; max-width: 400px; border: 1px solid var(--border); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
        .modal h2 { margin-bottom: 20px; font-size: 20px; }
        .modal .buttons { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
        .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text-main); }
        .btn-outline:hover { background: var(--bg-hover); }

        /* Toast Notifications */
        #toast-container { position: fixed; top: 24px; right: 24px; z-index: 3000; display: flex; flex-direction: column; gap: 10px; }
        .toast { background: var(--bg-panel); color: var(--text-main); padding: 16px 24px; border-radius: 8px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); border-left: 4px solid var(--primary); animation: slideIn 0.3s ease-out forwards; display: flex; align-items: center; gap: 12px; min-width: 250px; }
        .toast.error { border-left-color: var(--danger); }
        .toast.success { border-left-color: var(--success); }

        /* Upload Manager */
        #upload-manager { position: fixed; bottom: 24px; right: 24px; width: 380px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 15px 30px rgba(0,0,0,0.6); z-index: 1500; display: none; flex-direction: column; overflow: hidden; transition: transform 0.3s; }
        #upload-manager.minimized .upload-list-container { display: none; }
        .upload-header { background: rgba(0,0,0,0.3); padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-weight: 600; border-bottom: 1px solid var(--border); }
        .upload-header:hover { background: rgba(0,0,0,0.4); }
        .upload-list-container { max-height: 350px; overflow-y: auto; padding: 12px 16px; background: var(--bg-panel); }
        .upload-item { margin-bottom: 16px; }
        .upload-item:last-child { margin-bottom: 0; }
        .upload-info { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
        .upload-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
        .upload-stats { color: var(--text-muted); font-size: 12px; }
        .upload-bar-bg { height: 6px; background: var(--bg-dark); border-radius: 3px; overflow: hidden; }
        .upload-bar-fill { height: 100%; background: var(--primary); width: 0%; transition: width 0.1s linear; }
        .upload-item.success .upload-bar-fill { background: var(--success); }
        .upload-item.error .upload-bar-fill { background: var(--danger); }

        /* Drag & Drop Overlay */
        #drop-zone { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(59, 130, 246, 0.1); border: 2px dashed var(--primary); border-radius: 12px; display: none; align-items: center; justify-content: center; z-index: 500; backdrop-filter: blur(2px); }
        #drop-zone.active { display: flex; animation: pulse 1.5s infinite; }
        .drop-message { pointer-events: none; font-size: 24px; font-weight: 600; color: var(--primary); background: var(--bg-panel); padding: 20px 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }

        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes fadeOut { to { opacity: 0; } }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); } 70% { box-shadow: 0 0 0 15px rgba(59, 130, 246, 0); } 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); } }

        /* Responsive */
        @media (max-width: 768px) {
            .file-size, .file-date { display: none; }
            .file-row { grid-template-columns: auto 1fr auto; padding: 12px 16px; }
            header { flex-direction: column; gap: 16px; align-items: flex-start; padding: 16px; }
            .header-right { width: 100%; justify-content: space-between; flex-direction: column-reverse; align-items: stretch; gap: 16px; }
            .storage-info { align-items: flex-start; }
            .user-info { width: 100%; justify-content: space-between; border-left: none; padding-left: 0; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
            .toolbar { flex-direction: column; align-items: stretch; }
            #upload-manager { width: calc(100% - 48px); bottom: 24px; right: 24px; }
        }
    </style>
</head>
<body>

    <!-- Login Screen -->
    <div id="login-screen">
        <div class="login-box">
            <h1>Xtron Upload Center</h1>
            <p>Enter your Access ID to continue</p>
            <form id="login-form">
                <div class="input-group">
                    <input type="text" id="access-id" placeholder="Access ID" autocomplete="off" required>
                </div>
                <button type="submit" style="width: 100%; justify-content: center; padding: 12px;">Access System</button>
            </form>
        </div>
    </div>

    <!-- Main App -->
    <div id="app-screen">
        <header>
            <div class="brand">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                Xtron Upload Center
            </div>
            <div class="header-right">
                <div class="storage-info hidden" id="storage-container">
                    <div class="storage-text"><span id="storage-free">--</span> free of <span id="storage-total">--</span></div>
                    <div class="storage-bar"><div class="storage-bar-fill" id="storage-fill"></div></div>
                </div>
                <div class="user-info">
                    <span class="role-badge" id="user-role-badge">View Only</span>
                    <button class="btn-outline" onclick="logout()" style="padding: 6px 12px; font-size: 13px;">Logout</button>
                </div>
            </div>
        </header>

        <main id="main-drop-area">
            <div class="toolbar">
                <div class="breadcrumbs" id="breadcrumbs"></div>
                <div class="actions full-access-only hidden">
                    <button onclick="showModal('folder-modal')">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path><line x1="12" y1="11" x2="12" y2="17"></line><line x1="9" y1="14" x2="15" y2="14"></line></svg>
                        New Folder
                    </button>
                    <input type="file" id="file-input" style="display: none;" multiple>
                    <button onclick="document.getElementById('file-input').click()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                        Upload File
                    </button>
                </div>
            </div>

            <div class="file-list">
                <div id="drop-zone"><div class="drop-message">Drop files here to upload</div></div>
                <div class="file-row file-header">
                    <div></div>
                    <div>Name</div>
                    <div class="file-size">Size</div>
                    <div class="file-date">Modified</div>
                    <div style="text-align: right;">Actions</div>
                </div>
                <div id="file-list-body"></div>
            </div>
        </main>
    </div>

    <!-- Modals -->
    <div class="modal-overlay" id="folder-modal">
        <div class="modal">
            <h2>Create New Folder</h2>
            <input type="text" id="new-folder-name" placeholder="Folder Name">
            <div class="buttons">
                <button class="btn-outline" onclick="hideModal('folder-modal')">Cancel</button>
                <button onclick="createFolder()">Create</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="rename-modal">
        <div class="modal">
            <h2>Rename Item</h2>
            <input type="hidden" id="rename-old-name">
            <input type="text" id="rename-new-name" placeholder="New Name">
            <div class="buttons">
                <button class="btn-outline" onclick="hideModal('rename-modal')">Cancel</button>
                <button onclick="renameItem()">Rename</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="move-modal">
        <div class="modal">
            <h2>Move Item</h2>
            <p id="move-item-name" style="margin-bottom: 12px; color: var(--text-muted); font-size: 14px; word-break: break-all;"></p>
            <input type="hidden" id="move-source-name">
            <label style="display:block; margin-bottom:6px; font-size: 13px; color:var(--text-muted);">Select Destination Folder:</label>
            <select id="move-destination"></select>
            <div class="buttons">
                <button class="btn-outline" onclick="hideModal('move-modal')">Cancel</button>
                <button onclick="moveItem()">Move Here</button>
            </div>
        </div>
    </div>

    <div id="toast-container"></div>

    <!-- Upload Manager -->
    <div id="upload-manager">
        <div class="upload-header" onclick="document.getElementById('upload-manager').classList.toggle('minimized')">
            <span id="upload-title">Uploading...</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        <div class="upload-list-container" id="upload-list"></div>
    </div>

    <script>
        // State
        let currentPath = '';
        let userRole = 'view';
        let activeUploads = 0;

        // Icons
        const icons = {
            folder: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`,
            file: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>`,
            download: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`,
            edit: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`,
            move: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><polyline points="15 10 20 15 15 20"></polyline><path d="M4 4v7a4 4 0 0 0 4 4h12"></path></svg>`,
            trash: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`
        };

        // Utility: Format Size
        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        // Utility: Toast
        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = message;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.animation = 'fadeOut 0.3s ease-out forwards';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // UI toggles
        function showModal(id) { 
            document.getElementById(id).style.display = 'flex'; 
            const input = document.querySelector(`#${id} input[type="text"]`);
            if(input) input.focus();
        }
        function hideModal(id) { 
            document.getElementById(id).style.display = 'none'; 
            document.querySelectorAll(`#${id} input[type="text"]`).forEach(i => i.value = '');
        }

        // Authentication Check
        function checkAuthOnLoad() {
            // Directly query the API to validate session, bypassing JS cookie restrictions
            fetch('api/list?path=').then(res => {
                if (res.status === 200) {
                    res.headers.forEach((val, key) => {
                        if(key.toLowerCase() === 'x-user-role') setRole(val);
                    });
                    showApp();
                } else {
                    document.getElementById('login-screen').style.display = 'flex';
                }
            }).catch(() => {
                document.getElementById('login-screen').style.display = 'flex';
            });
        }

        function setRole(role) {
            userRole = role;
            document.getElementById('user-role-badge').innerText = role === 'full' ? 'Full Access' : 'View Only';
            if (role === 'full') {
                document.querySelectorAll('.full-access-only').forEach(el => el.classList.remove('hidden'));
            } else {
                document.querySelectorAll('.full-access-only').forEach(el => el.classList.add('hidden'));
            }
        }

        // Auth
        document.getElementById('login-form').onsubmit = async (e) => {
            e.preventDefault();
            const id = document.getElementById('access-id').value;
            try {
                const res = await fetch('api/login', {
                    method: 'POST',
                    body: JSON.stringify({ id }),
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                if (data.success) {
                    setRole(data.role);
                    showToast('Access Granted');
                    showApp();
                } else {
                    showToast('Invalid Access ID', 'error');
                }
            } catch (err) {
                showToast('Connection error', 'error');
            }
        };

        async function logout() {
            await fetch('api/logout', { method: 'POST' });
            document.cookie = "session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            location.reload();
        }

        function showApp() {
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('app-screen').style.display = 'flex';
            loadStorageInfo();
            loadDirectory(currentPath);
        }

        // Storage Info
        async function loadStorageInfo() {
            try {
                const res = await fetch('api/storage');
                if (!res.ok) return;
                const data = await res.json();
                
                document.getElementById('storage-container').classList.remove('hidden');
                document.getElementById('storage-free').innerText = formatSize(data.free);
                document.getElementById('storage-total').innerText = formatSize(data.total);
                
                const percentUsed = (data.used / data.total) * 100;
                const fill = document.getElementById('storage-fill');
                fill.style.width = `${percentUsed}%`;
                
                if (percentUsed > 90) fill.style.backgroundColor = 'var(--danger)';
                else if (percentUsed > 75) fill.style.backgroundColor = 'var(--warning)';
                else fill.style.backgroundColor = 'var(--success)';
            } catch (err) {
                console.error("Failed to load storage info", err);
            }
        }

        // Navigation & Listing
        async function loadDirectory(path) {
            currentPath = path;
            renderBreadcrumbs();
            const tbody = document.getElementById('file-list-body');
            tbody.innerHTML = `<div class="empty-state">Loading...</div>`;
            
            try {
                const res = await fetch(`api/list?path=${encodeURIComponent(path)}`);
                if (!res.ok) throw new Error('Failed to load directory');
                const files = await res.json();
                
                if (files.length === 0) {
                    tbody.innerHTML = `<div class="empty-state">${icons.folder}<div>Folder is empty</div></div>`;
                    return;
                }

                files.sort((a, b) => {
                    if (a.is_dir === b.is_dir) return a.name.localeCompare(b.name);
                    return a.is_dir ? -1 : 1;
                });

                tbody.innerHTML = files.map(f => {
                    const fullPath = (currentPath === '' ? '' : currentPath + '/') + f.name;
                    const dlUrl = `api/download?path=${encodeURIComponent(fullPath)}`;
                    
                    let actionsHtml = `<a href="${dlUrl}" class="icon-btn" title="Download" download>${icons.download}</a>`;
                    
                    if (userRole === 'full') {
                        actionsHtml += `
                            <button class="icon-btn" title="Move" onclick="promptMove('${f.name}')">${icons.move}</button>
                            <button class="icon-btn" title="Rename" onclick="promptRename('${f.name}')">${icons.edit}</button>
                            <button class="icon-btn danger" title="Delete" onclick="deleteItem('${f.name}')">${icons.trash}</button>
                        `;
                    }

                    const nameClick = f.is_dir ? `onclick="loadDirectory('${fullPath}')"` : `href="${dlUrl}" target="_blank"`;
                    const nameTag = f.is_dir ? 'span' : 'a';

                    return `
                    <div class="file-row">
                        <div class="file-icon">${f.is_dir ? icons.folder : icons.file}</div>
                        <${nameTag} class="file-name" ${nameClick}>${f.name}</${nameTag}>
                        <div class="file-size">${f.is_dir ? '-' : formatSize(f.size)}</div>
                        <div class="file-date">${f.modified}</div>
                        <div class="file-actions">${actionsHtml}</div>
                    </div>`;
                }).join('');

            } catch (err) {
                tbody.innerHTML = `<div class="empty-state" style="color:var(--danger)">Error loading directory</div>`;
                showToast(err.message, 'error');
            }
        }

        function renderBreadcrumbs() {
            const container = document.getElementById('breadcrumbs');
            const parts = currentPath.split('/').filter(p => p);
            
            let html = `<span class="breadcrumb-item ${parts.length === 0 ? 'breadcrumb-active' : ''}" onclick="loadDirectory('')">Home</span>`;
            
            let accumPath = '';
            parts.forEach((part, index) => {
                accumPath += (accumPath ? '/' : '') + part;
                html += `<span class="breadcrumb-sep">/</span>`;
                const isActive = index === parts.length - 1;
                html += `<span class="breadcrumb-item ${isActive ? 'breadcrumb-active' : ''}" onclick="loadDirectory('${accumPath}')">${part}</span>`;
            });
            
            container.innerHTML = html;
        }

        // File Operations
        async function createFolder() {
            const name = document.getElementById('new-folder-name').value.trim();
            if (!name) return;
            const target = (currentPath === '' ? '' : currentPath + '/') + name;
            try {
                const res = await fetch('api/mkdir', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: target}) });
                if (!res.ok) throw new Error(await res.text());
                hideModal('folder-modal');
                showToast('Folder created');
                loadDirectory(currentPath);
            } catch (err) { showToast(err.message, 'error'); }
        }

        function promptRename(oldName) {
            document.getElementById('rename-old-name').value = oldName;
            document.getElementById('rename-new-name').value = oldName;
            showModal('rename-modal');
        }

        async function renameItem() {
            const oldName = document.getElementById('rename-old-name').value;
            const newName = document.getElementById('rename-new-name').value.trim();
            if (!newName || oldName === newName) return hideModal('rename-modal');
            const oldPath = (currentPath === '' ? '' : currentPath + '/') + oldName;
            const newPath = (currentPath === '' ? '' : currentPath + '/') + newName;
            try {
                const res = await fetch('api/rename', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({old_path: oldPath, new_path: newPath}) });
                if (!res.ok) throw new Error(await res.text());
                hideModal('rename-modal');
                showToast('Item renamed');
                loadDirectory(currentPath);
            } catch (err) { showToast(err.message, 'error'); }
        }

        async function promptMove(itemName) {
            document.getElementById('move-source-name').value = itemName;
            document.getElementById('move-item-name').innerText = itemName;
            
            try {
                const res = await fetch('api/folders');
                if (!res.ok) throw new Error('Could not load folders');
                const folders = await res.json();
                
                const select = document.getElementById('move-destination');
                select.innerHTML = folders.map(f => `<option value="${f}">${f}</option>`).join('');
                
                // Pre-select current folder so it doesn't accidentally move to root
                const currentFolderValue = currentPath === '' ? '/' : '/' + currentPath;
                if (Array.from(select.options).some(opt => opt.value === currentFolderValue)) {
                    select.value = currentFolderValue;
                }

                showModal('move-modal');
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        async function moveItem() {
            const itemName = document.getElementById('move-source-name').value;
            const destFolder = document.getElementById('move-destination').value;
            
            const sourcePath = (currentPath === '' ? '' : currentPath + '/') + itemName;
            
            try {
                const res = await fetch('api/move', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({source: sourcePath, destination: destFolder}) 
                });
                if (!res.ok) throw new Error(await res.text());
                
                hideModal('move-modal');
                showToast('Item moved successfully');
                loadDirectory(currentPath);
            } catch (err) { 
                showToast(err.message, 'error'); 
            }
        }

        async function deleteItem(name) {
            if (!confirm(`Are you sure you want to delete ${name}?`)) return;
            const target = (currentPath === '' ? '' : currentPath + '/') + name;
            try {
                const res = await fetch('api/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path: target}) });
                if (!res.ok) throw new Error(await res.text());
                showToast('Item deleted');
                loadStorageInfo();
                loadDirectory(currentPath);
            } catch (err) { showToast(err.message, 'error'); }
        }

        // --- ADVANCED UPLOAD LOGIC ---
        function handleFiles(files) {
            if (!files.length) return;
            document.getElementById('upload-manager').style.display = 'flex';
            document.getElementById('upload-manager').classList.remove('minimized');

            let promises = [];
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const targetPath = (currentPath === '' ? '' : currentPath + '/') + file.name;
                promises.push(uploadFileWithProgress(file, targetPath));
            }

            Promise.allSettled(promises).then(() => {
                loadStorageInfo();
                loadDirectory(currentPath);
            });
        }

        document.getElementById('file-input').addEventListener('change', function() {
            handleFiles(this.files);
            this.value = ''; // reset
        });

        // Drag and Drop Logic
        const dropArea = document.getElementById('main-drop-area');
        const dropZone = document.getElementById('drop-zone');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                if (userRole === 'full') dropZone.classList.add('active');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                if(e.target === dropZone) dropZone.classList.remove('active');
            }, false);
        });

        dropArea.addEventListener('drop', (e) => {
            dropZone.classList.remove('active');
            if (userRole !== 'full') return showToast('Permission denied', 'error');
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }, false);

        // XHR Upload Engine
        function uploadFileWithProgress(file, targetPath) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                const uploadId = 'up-' + Math.random().toString(36).substr(2, 9);
                createUploadUI(uploadId, file.name);

                activeUploads++;
                updateUploadTitle();
                let startTime = Date.now();

                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = (e.loaded / e.total) * 100;
                        const timeElapsed = (Date.now() - startTime) / 1000;
                        const speed = timeElapsed > 0 ? (e.loaded / timeElapsed) : 0;
                        updateUploadUI(uploadId, percent, speed, e.loaded, e.total);
                    }
                });

                xhr.addEventListener('load', () => {
                    activeUploads--;
                    updateUploadTitle();
                    if (xhr.status >= 200 && xhr.status < 300) {
                        completeUploadUI(uploadId);
                        resolve();
                    } else {
                        failUploadUI(uploadId, xhr.statusText);
                        reject(new Error(xhr.statusText));
                    }
                });

                xhr.addEventListener('error', () => {
                    activeUploads--;
                    updateUploadTitle();
                    failUploadUI(uploadId, 'Network Error');
                    reject(new Error('Network Error'));
                });

                xhr.open('POST', `api/upload?path=${encodeURIComponent(targetPath)}`);
                xhr.setRequestHeader('Content-Type', 'application/octet-stream');
                xhr.send(file);
            });
        }

        // Upload UI Handlers
        function createUploadUI(id, filename) {
            const list = document.getElementById('upload-list');
            const html = `
            <div class="upload-item" id="${id}">
                <div class="upload-info">
                    <span class="upload-name" title="${filename}">${filename}</span>
                    <span class="upload-stats" id="${id}-stats">Starting...</span>
                </div>
                <div class="upload-bar-bg">
                    <div class="upload-bar-fill" id="${id}-fill"></div>
                </div>
            </div>`;
            list.insertAdjacentHTML('afterbegin', html);
        }

        function updateUploadUI(id, percent, speedBytes, loaded, total) {
            const fill = document.getElementById(`${id}-fill`);
            const stats = document.getElementById(`${id}-stats`);
            if (fill) fill.style.width = `${percent}%`;
            if (stats) stats.innerText = `${formatSize(speedBytes)}/s - ${Math.round(percent)}%`;
        }

        function completeUploadUI(id) {
            const item = document.getElementById(id);
            const stats = document.getElementById(`${id}-stats`);
            if (item) item.classList.add('success');
            if (stats) stats.innerText = `Complete`;
        }

        function failUploadUI(id, msg) {
            const item = document.getElementById(id);
            const stats = document.getElementById(`${id}-stats`);
            if (item) item.classList.add('error');
            if (stats) stats.innerText = `Failed`;
        }

        function updateUploadTitle() {
            const title = document.getElementById('upload-title');
            if (activeUploads > 0) {
                title.innerText = `Uploading ${activeUploads} file(s)...`;
            } else {
                title.innerText = `Uploads Complete`;
            }
        }

        // Init
        checkAuthOnLoad();
    </script>
</body>
</html>
"""

# ================= Backend Server Logic =================

def get_safe_path(user_path):
    """Prevents directory traversal attacks by securely resolving paths against UPLOAD_DIR."""
    user_path = urllib.parse.unquote(user_path)
    # Remove slashes so os.path.join doesn't reset to system root
    user_path = user_path.strip('/').strip('\\')
    full_path = os.path.normpath(os.path.join(UPLOAD_DIR, user_path))
    # Ensure it's inside our designated UPLOAD_DIR
    if not full_path.startswith(os.path.abspath(UPLOAD_DIR)):
        return None
    return full_path

class XtronHandler(BaseHTTPRequestHandler):
    
    def load_users(self):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def get_session(self):
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return None
        
        cookies = {}
        for item in cookie_header.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k] = v
        
        token = cookies.get('session')
        if token and token in SESSIONS:
            return SESSIONS[token]
        return None

    def send_json(self, data, status=200, headers=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_text_error(self, message, status=400):
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        qs = urllib.parse.parse_qs(parsed_url.query)

        # Serve the Single Page App
        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_APP.encode('utf-8'))
            return

        # Handle API routes
        if path.startswith('/api/'):
            user = self.get_session()
            if not user:
                self.send_text_error("Unauthorized", 401)
                return

            # Storage Information
            if path == '/api/storage':
                try:
                    total, used, free = shutil.disk_usage(UPLOAD_DIR)
                    self.send_json({
                        "total": total,
                        "used": used,
                        "free": free
                    })
                except Exception as e:
                    self.send_text_error(str(e), 500)
                return

            # Directory Listing
            if path == '/api/list':
                req_path = qs.get('path', [''])[0]
                safe_path = get_safe_path(req_path)
                
                if not safe_path or not os.path.exists(safe_path) or not os.path.isdir(safe_path):
                    self.send_text_error("Directory not found", 404)
                    return
                
                files = []
                for entry in os.scandir(safe_path):
                    stat = entry.stat()
                    dt = datetime.fromtimestamp(stat.st_mtime)
                    files.append({
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size,
                        "modified": dt.strftime("%Y-%m-%d %H:%M")
                    })
                # Pass role in header so frontend can verify on load
                self.send_json(files, headers={'X-User-Role': user['role']})
                return

            # Get list of all folders recursively for the "Move" dropdown
            if path == '/api/folders':
                if user['role'] != 'full':
                    self.send_text_error("Forbidden", 403)
                    return
                
                folders = ['/'] # root directory representation
                for root, dirs, _ in os.walk(UPLOAD_DIR):
                    for d in dirs:
                        full_dir = os.path.join(root, d)
                        rel_dir = os.path.relpath(full_dir, UPLOAD_DIR)
                        # Normalize slashes for the frontend UI
                        folders.append('/' + rel_dir.replace('\\', '/'))
                self.send_json(folders)
                return

            # File Download
            if path == '/api/download':
                req_path = qs.get('path', [''])[0]
                safe_path = get_safe_path(req_path)

                if not safe_path or not os.path.exists(safe_path) or not os.path.isfile(safe_path):
                    self.send_text_error("File not found", 404)
                    return
                
                try:
                    size = os.path.getsize(safe_path)
                    mtype, _ = mimetypes.guess_type(safe_path)
                    mtype = mtype or 'application/octet-stream'
                    
                    self.send_response(200)
                    self.send_header('Content-Type', mtype)
                    self.send_header('Content-Length', str(size))
                    # Force download
                    filename = urllib.parse.quote(os.path.basename(safe_path))
                    self.send_header('Content-Disposition', f'attachment; filename*=UTF-8\'\'{filename}')
                    self.end_headers()
                    
                    with open(safe_path, 'rb') as f:
                        shutil.copyfileobj(f, self.wfile)
                except (ConnectionResetError, BrokenPipeError):
                    # Client disconnected mid-download, ignore safely
                    pass
                except Exception as e:
                    print(f"Download Error: {e}")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        qs = urllib.parse.parse_qs(parsed_url.query)

        # Handle Login
        if path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                access_id = data.get('id', '')
                users = self.load_users()
                
                if access_id in users:
                    token = str(uuid.uuid4())
                    role = users[access_id].get('role', 'view')
                    SESSIONS[token] = {"id": access_id, "role": role}
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Set-Cookie', f'session={token}; Path=/; Max-Age=2592000') # 30 Days expiration
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "role": role}).encode('utf-8'))
                else:
                    self.send_json({"success": False}, 401)
            except Exception as e:
                self.send_text_error(str(e), 400)
            return
            
        # Handle Logout
        if path == '/api/logout':
            self.send_response(200)
            self.send_header('Set-Cookie', 'session=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        # Validate Session for other POST requests
        user = self.get_session()
        if not user:
            self.send_text_error("Unauthorized", 401)
            return

        # All following operations require 'full' access role
        if user['role'] != 'full':
            self.send_text_error("Permission Denied: View Only Access", 403)
            return

        # File Upload (Raw binary stream)
        if path == '/api/upload':
            req_path = qs.get('path', [''])[0]
            if not req_path:
                self.send_text_error("Path required", 400)
                return
                
            safe_path = get_safe_path(req_path)
            if not safe_path:
                self.send_text_error("Invalid path", 400)
                return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_text_error("Empty file", 400)
                return

            try:
                # Stream writing to handle large files efficiently (64KB chunks)
                bytes_read = 0
                chunk_size = 65536
                with open(safe_path, 'wb') as f:
                    while bytes_read < content_length:
                        read_size = min(chunk_size, content_length - bytes_read)
                        chunk = self.rfile.read(read_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_read += len(chunk)
                self.send_json({"success": True})
            except Exception as e:
                self.send_text_error(str(e), 500)
            return

        # Parse JSON body for the rest of POST endpoints
        content_length = int(self.headers.get('Content-Length', 0))
        body_data = {}
        if content_length > 0:
            try:
                body = self.rfile.read(content_length).decode('utf-8')
                body_data = json.loads(body)
            except Exception:
                self.send_text_error("Invalid JSON body", 400)
                return

        # Create Directory
        if path == '/api/mkdir':
            target_path = body_data.get('path', '')
            safe_path = get_safe_path(target_path)
            if not safe_path:
                self.send_text_error("Invalid path", 400)
                return
            try:
                os.makedirs(safe_path, exist_ok=True)
                self.send_json({"success": True})
            except Exception as e:
                self.send_text_error(str(e), 500)
            return

        # Delete File/Directory
        if path == '/api/delete':
            target_path = body_data.get('path', '')
            safe_path = get_safe_path(target_path)
            if not safe_path or not os.path.exists(safe_path):
                self.send_text_error("Path not found", 404)
                return
            # Prevent deleting root upload dir
            if safe_path == os.path.abspath(UPLOAD_DIR):
                self.send_text_error("Cannot delete root directory", 403)
                return
                
            try:
                if os.path.isdir(safe_path):
                    shutil.rmtree(safe_path)
                else:
                    os.remove(safe_path)
                self.send_json({"success": True})
            except Exception as e:
                self.send_text_error(str(e), 500)
            return

        # Rename File/Directory
        if path == '/api/rename':
            old_path = body_data.get('old_path', '')
            new_path = body_data.get('new_path', '')
            
            safe_old = get_safe_path(old_path)
            safe_new = get_safe_path(new_path)
            
            if not safe_old or not safe_new or not os.path.exists(safe_old):
                self.send_text_error("Invalid path", 400)
                return
                
            if safe_old == os.path.abspath(UPLOAD_DIR):
                self.send_text_error("Cannot rename root directory", 403)
                return
                
            try:
                os.rename(safe_old, safe_new)
                self.send_json({"success": True})
            except Exception as e:
                self.send_text_error(str(e), 500)
            return

        # Move File/Directory
        if path == '/api/move':
            source_path = body_data.get('source', '')
            dest_dir = body_data.get('destination', '')
            
            safe_source = get_safe_path(source_path)
            safe_dest_dir = get_safe_path(dest_dir)
            
            if not safe_source or not safe_dest_dir or not os.path.exists(safe_source) or not os.path.isdir(safe_dest_dir):
                self.send_text_error("Invalid paths provided", 400)
                return
                
            if safe_source == os.path.abspath(UPLOAD_DIR):
                self.send_text_error("Cannot move root directory", 403)
                return
            
            item_name = os.path.basename(safe_source)
            safe_dest_file = os.path.join(safe_dest_dir, item_name)
            
            # Prevent moving a folder into itself
            if safe_dest_file.startswith(safe_source + os.sep) or safe_dest_file == safe_source:
                self.send_text_error("Cannot move a folder into itself or the exact same location", 400)
                return
                
            try:
                shutil.move(safe_source, safe_dest_file)
                self.send_json({"success": True})
            except Exception as e:
                self.send_text_error(str(e), 500)
            return

        self.send_error(404, "Endpoint not found")

# ================= Server Execution =================
if __name__ == '__main__':
    # Use ThreadingHTTPServer so large uploads don't block other requests
    server = ThreadingHTTPServer((HOST, PORT), XtronHandler)
    print(f"[*] Xtron Upload Center is running on http://{HOST}:{PORT}")
    print(f"[*] Serving files from: {UPLOAD_DIR}")
    print(f"[*] Using auth file: {USERS_FILE}")
    print(f"[*] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down Xtron Upload Center.")
        server.server_close()

