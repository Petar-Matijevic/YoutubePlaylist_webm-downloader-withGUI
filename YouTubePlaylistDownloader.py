import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import os
import threading
import json
from typing import Dict


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YT Audio Downloader")
        self.root.geometry("800x600")
        self.setup_ui()
        self.load_settings()
        self.download_thread = None
        self.stop_flag = False

    def setup_ui(self):
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=6, font=('Arial', 10))
        style.configure('TProgressbar', thickness=25)

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # URL Input
        url_frame = ttk.LabelFrame(main_frame, text="Playlist URL")
        url_frame.pack(fill=tk.X, pady=5)
        self.url_entry = ttk.Entry(url_frame, font=('Arial', 12))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(url_frame, text="Paste", command=self.paste_url).pack(side=tk.LEFT, padx=5)

        # Output Directory
        dir_frame = ttk.LabelFrame(main_frame, text="Output Location")
        dir_frame.pack(fill=tk.X, pady=5)
        self.dir_entry = ttk.Entry(dir_frame, font=('Arial', 12))
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(dir_frame, text="Browse", command=self.choose_directory).pack(side=tk.LEFT, padx=5)

        # Progress Display
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.tree = ttk.Treeview(progress_frame, columns=('status', 'progress'), show='headings')
        self.tree.heading('status', text='Status')
        self.tree.heading('progress', text='Progress')
        self.tree.column('status', width=100)
        self.tree.column('progress', width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Overall Progress
        self.overall_progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.overall_progress.pack(fill=tk.X, padx=5, pady=5)

        # Control Buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        self.start_btn = ttk.Button(control_frame, text="Start Download", command=self.start_download)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_download, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Settings Button
        ttk.Button(control_frame, text="⚙️", command=self.open_settings).pack(side=tk.RIGHT, padx=5)

        # Log Console
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        ttk.Label(settings_window, text="Max Concurrent Downloads:").grid(row=0, column=0, padx=5, pady=5)
        self.concurrent_var = tk.StringVar(value=str(self.settings.get('concurrent', 3)))
        ttk.Spinbox(settings_window, from_=1, to=10, textvariable=self.concurrent_var).grid(row=0, column=1, padx=5,
                                                                                            pady=5)

        ttk.Label(settings_window, text="Download Format:").grid(row=1, column=0, padx=5, pady=5)
        self.format_var = tk.StringVar(value=self.settings.get('format', 'webm'))
        ttk.Combobox(settings_window, textvariable=self.format_var,
                     values=['webm', 'mp3', 'm4a']).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(settings_window, text="Max Retries:").grid(row=2, column=0, padx=5, pady=5)
        self.retries_var = tk.StringVar(value=str(self.settings.get('retries', 5)))
        ttk.Spinbox(settings_window, from_=0, to=10, textvariable=self.retries_var).grid(row=2, column=1, padx=5,
                                                                                         pady=5)

        ttk.Button(settings_window, text="Save", command=self.save_settings).grid(row=3, columnspan=2, pady=10)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                'concurrent': 3,
                'format': 'webm',
                'retries': 5
            }

    def save_settings(self):
        self.settings = {
            'concurrent': int(self.concurrent_var.get()),
            'format': self.format_var.get(),
            'retries': int(self.retries_var.get())
        }
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
        messagebox.showinfo("Settings Saved", "Settings have been updated successfully")

    def paste_url(self):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, self.root.clipboard_get())

    def choose_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, path)

    def log_message(self, message, level="info"):
        color_map = {
            "error": "red",
            "warning": "orange",
            "success": "green",
            "info": "black"
        }
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", level)
        self.log_text.tag_config(level, foreground=color_map.get(level, "black"))
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_download(self):
        if not self.url_entry.get() or not self.dir_entry.get():
            messagebox.showerror("Error", "Please provide a playlist URL and output directory")
            return

        self.stop_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.tree.delete(*self.tree.get_children())
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.download_thread = threading.Thread(target=self.run_download)
        self.download_thread.start()

    def stop_download(self):
        self.stop_flag = True
        self.log_message("Stopping download...", "warning")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def run_download(self):
        ydl_opts = {
            'format': f'bestaudio[ext={self.settings["format"]}]/bestaudio/best',
            'outtmpl': os.path.join(self.dir_entry.get(), '%(title)s.%(ext)s'),
            'ignoreerrors': True,
            'retries': self.settings['retries'],
            'concurrent_fragment_downloads': self.settings['concurrent'],
            'progress_hooks': [self.progress_hook],
            'postprocessors': [],
            'socket_timeout': 30,
            'noprogress': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_message(f"Starting download of {self.url_entry.get()}", "info")
                result = ydl.download([self.url_entry.get()])
                self.log_message("Download completed!", "success")
        except Exception as e:
            self.log_message(f"Error: {str(e)}", "error")
        finally:
            self.root.after(0, self.on_download_finish)

    def progress_hook(self, d):
        if self.stop_flag:
            raise yt_dlp.DownloadCancelled()

        if d['status'] == 'downloading':
            self.root.after(0, self.update_progress, d)
        elif d['status'] == 'error':
            self.root.after(0, self.log_message, f"Error downloading {d['filename']}: {d['error']}", "error")

    def update_progress(self, d):
        item_id = d['info_dict']['id']
        if not self.tree.exists(item_id):
            self.tree.insert('', tk.END, iid=item_id,
                             values=(d['info_dict']['title'], '0%'))

        progress = f"{d['downloaded_bytes'] / d['total_bytes'] * 100:.1f}%"
        self.tree.item(item_id, values=(d['info_dict']['title'], progress))

    def on_download_finish(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        messagebox.showinfo("Complete", "Download process finished!")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()