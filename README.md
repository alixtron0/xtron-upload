# Xtron Upload Center

A lightweight, self-contained, and secure web-based file management system. Xtron allows users to upload, download, organize, and manage files through a modern, responsive dashboard—all powered by a single Python script.

## 🚀 Key Features

* **Zero Dependencies**: Runs on standard Python 3.x with no need for `pip install`.
* **Role-Based Access**: 
    * **Admin**: Full control (Upload, Delete, Rename, Move, Create Folders).
    * **Viewer**: Restricted to viewing and downloading files only.
* **Modern UI**: Dark-mode interface with breadcrumb navigation, drag-and-drop support, and real-time upload progress bars.
* **Storage Insights**: Visual bar showing free vs. used disk space on the server.
* **Secure**: Built-in protections against directory traversal attacks.
* **Multi-threaded**: Uses threading to handle multiple concurrent uploads/downloads without blocking the UI.

## 🛠️ Requirements

* **Python 3.6+**
* **No external libraries required.**

## 📥 Installation & Usage

1.  **Download the script**: Save `server.py` to your desired directory.
2.  **Run the server**:
    ```bash
    python server.py
    ```
3.  **Access the Dashboard**: Open your browser and navigate to `http://localhost:8080`.

## 🔐 Default Credentials

Upon the first run, the system creates a `users.json` file. The default Access IDs are:

| Role | Access ID |
| :--- | :--- |
| **Admin** | `xtron_admin_123` |
| **Viewer** | `xtron_view_456` |

> [!TIP]
> You can add or modify users by editing the `users.json` file. No server restart is required for user changes to take effect.

## 📂 Project Structure

* `server.py`: The core application containing the Backend logic and the Frontend SPA (HTML/CSS/JS).
* `/uploads`: The directory where all your files are stored (created automatically).
* `users.json`: Stores user IDs and permissions (created automatically).

## 🛡️ Security Note

While Xtron includes safety features like path normalization and session tokens, it is intended for use within private networks or for personal utility. If exposing this to the public internet, it is recommended to run it behind a reverse proxy (like Nginx) with HTTPS enabled.

---

**Built with simplicity in mind.** 🛰️
