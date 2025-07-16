import sys
import subprocess
import re
import os
import sqlite3
import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QDialog,
    QFormLayout, QListWidget, QListWidgetItem, QMessageBox,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QColor, QFont

ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')

class DatabaseManager:
    def __init__(self, db_dir="db", db_name="shellrunner.db"):
        self.db_dir = db_dir
        self.db_path = os.path.join(self.db_dir, db_name)
        self.conn = None
        self.cursor = None
        self.ensure_db_directory()
        self.connect()
        self.create_tables()

    def ensure_db_directory(self):
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def close(self):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        if not self.cursor:
            return

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                command TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                timestamp TEXT NOT NULL,
                log_line TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def insert_task(self, name, command, description):
        if not self.cursor:
            return None
        start_time = datetime.datetime.now().isoformat()
        self.cursor.execute("INSERT INTO tasks (name, command, description, status, start_time) VALUES (?, ?, ?, ?, ?)",
                            (name, command, description, "Pending", start_time))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_task_status(self, task_id, status):
        if not self.cursor:
            return
        end_time = datetime.datetime.now().isoformat() if status in ["Completed", "Interrupted", "Error"] else None
        self.cursor.execute("UPDATE tasks SET status = ?, end_time = ? WHERE id = ?", (status, end_time, task_id))
        self.conn.commit()

    def insert_log(self, task_id, log_line):
        if not self.cursor:
            return
        timestamp = datetime.datetime.now().isoformat()
        self.cursor.execute("INSERT INTO task_logs (task_id, timestamp, log_line) VALUES (?, ?, ?)",
                            (task_id, timestamp, log_line))
        self.conn.commit()

    def get_all_tasks(self):
        if not self.cursor:
            return []
        self.cursor.execute("SELECT id, name, command, description, status, start_time, end_time FROM tasks ORDER BY id")
        return self.cursor.fetchall()

    def get_task_logs(self, task_id):
        if not self.cursor:
            return []
        self.cursor.execute("SELECT timestamp, log_line FROM task_logs WHERE task_id = ? ORDER BY id", (task_id,))
        return self.cursor.fetchall()

class CommandRunner(QThread):
    output_signal = pyqtSignal(str)
    command_finished_signal = pyqtSignal(int, str)
    log_to_db_signal = pyqtSignal(int, str)

    def __init__(self, command, task_index, task_db_id):
        super().__init__()
        self.command = command
        self.task_index = task_index
        self.task_db_id = task_db_id
        self.process = None
        self.stop_requested = False
        self.mutex = QMutex()

    def run(self):
        self.output_signal.emit(f"\n[*] Running Task {self.task_index + 1}: '{self.command}'\n")
        self.output_signal.emit("-" * 60 + "\n")
        self.log_to_db_signal.emit(self.task_db_id, f"[*] Running Task: '{self.command}'")

        try:
            first_cmd_part = self.command.split()[0]
            if not any(os.access(os.path.join(path, first_cmd_part), os.X_OK) for path in os.environ.get("PATH", "").split(os.pathsep)):
                 if not os.path.exists(first_cmd_part) or not os.access(first_cmd_part, os.X_OK):
                    raise FileNotFoundError(f"Command '{first_cmd_part}' not found or not executable.")

            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in iter(self.process.stdout.readline, ''):
                self.mutex.lock()
                if self.stop_requested:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()

                clean_line = ansi_escape.sub('', line)
                self.output_signal.emit(clean_line)
                self.log_to_db_signal.emit(self.task_db_id, clean_line.strip())
            
            self.process.wait()

            self.mutex.lock()
            if self.stop_requested:
                self.output_signal.emit(f"\n[!] Task '{self.command}' was interrupted by user.\n")
                self.log_to_db_signal.emit(self.task_db_id, f"[!] Task '{self.command}' was interrupted by user.")
                self.command_finished_signal.emit(self.task_index, "Interrupted")
            else:
                if self.process.returncode == 0:
                    self.output_signal.emit(f"\n[✓] Task '{self.command}' completed successfully. (Exit Code: {self.process.returncode})\n")
                    self.log_to_db_signal.emit(self.task_db_id, f"[✓] Task '{self.command}' completed successfully. (Exit Code: {self.process.returncode})")
                    self.command_finished_signal.emit(self.task_index, "Completed")
                else:
                    self.output_signal.emit(f"\n[X] Task '{self.command}' failed. (Exit Code: {self.process.returncode})\n")
                    self.log_to_db_signal.emit(self.task_db_id, f"[X] Task '{self.command}' failed. (Exit Code: {self.process.returncode})")
                    self.command_finished_signal.emit(self.task_index, f"Error: Exit Code {self.process.returncode}")
            self.mutex.unlock()

        except FileNotFoundError as e:
            error_message = f"[X] Error: {e}\n"
            self.output_signal.emit(error_message)
            self.log_to_db_signal.emit(self.task_db_id, error_message.strip())
            self.command_finished_signal.emit(self.task_index, f"Error: Command Not Found")
        except Exception as e:
            error_message = f"[X] An unexpected error occurred while running '{self.command}': {e}\n"
            self.output_signal.emit(error_message)
            self.log_to_db_signal.emit(self.task_db_id, error_message.strip())
            self.command_finished_signal.emit(self.task_index, f"Error: {type(e).__name__}")
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=2)
                if self.process.poll() is None:
                    self.process.kill()
            self.process = None

        self.output_signal.emit("-" * 60 + "\n")
        self.log_to_db_signal.emit(self.task_db_id, "-" * 60)

    def stop_execution(self):
        self.mutex.lock()
        self.stop_requested = True
        if self.process:
            self.process.terminate()
        self.mutex.unlock()
        self.wait(500)
        if self.isRunning():
            if self.process and self.process.poll() is None:
                self.process.kill()
            self.output_signal.emit("[!] Forcefully stopping the command runner thread.\n")
            self.log_to_db_signal.emit(self.task_db_id, "[!] Forcefully stopping the command runner thread.")
            self.terminate()
            self.wait()

class Task:
    def __init__(self, name, command, description="", db_id=None):
        self.name = name
        self.command = command
        self.description = description
        self.status = "Pending"
        self.db_id = db_id

    def __str__(self):
        return f"[{self.status}] {self.name}: {self.command}"

class NewTaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Task")
        self.setGeometry(200, 200, 500, 300)
        self.task = task
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("")
        
        self.task_command_input = QLineEdit()
        self.task_command_input.setPlaceholderText("")
        
        self.task_description_input = QTextEdit()
        self.task_description_input.setPlaceholderText("")
        self.task_description_input.setFixedHeight(80)

        layout.addRow("Task Name:", self.task_name_input)
        layout.addRow("Command:", self.task_command_input)
        layout.addRow("Description:", self.task_description_input)

        if self.task:
            self.task_name_input.setText(self.task.name)
            self.task_command_input.setText(self.task.command)
            self.task_description_input.setText(self.task.description)

        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.validate_and_accept)
        save_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; }")
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; }")

        buttons_layout.addStretch(1)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addStretch(1)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def validate_and_accept(self):
        if not self.task_name_input.text().strip():
            QMessageBox.warning(self, "Input Error", "Task Name cannot be empty.")
            return
        if not self.task_command_input.text().strip():
            QMessageBox.warning(self.parent(), "Input Error", "Command cannot be empty.")
            return
        self.accept()

    def get_task_data(self):
        return {
            "name": self.task_name_input.text().strip(),
            "command": self.task_command_input.text().strip(),
            "description": self.task_description_input.toPlainText().strip()
        }

class ShellRunnerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.tasks = []
        self.current_running_thread = None
        self.current_task_index = -1
        self.reports_dir = "reports"
        self.ensure_reports_directory()
        self.init_ui()
        self.load_tasks_from_db()

    def ensure_reports_directory(self):
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)

    def init_ui(self):
        self.setWindowTitle("ShellRunner - Command Automation Tool")
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout()

        main_layout.addSpacing(15)

        tasks_and_output_section = QHBoxLayout()

        tasks_column_layout = QVBoxLayout()
        tasks_column_layout.addWidget(QLabel("<h2>Task List</h2>"))
        
        self.task_list_widget = QListWidget()
        self.task_list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.task_list_widget.setFont(QFont("Arial", 10))
        tasks_column_layout.addWidget(self.task_list_widget)

        task_buttons_layout = QHBoxLayout()
        blue_button_style = "QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; } QPushButton:disabled { background-color: #a0a0a0; }"
        red_button_style = "QPushButton { background-color: #F44336; color: white; padding: 8px; border-radius: 5px; } QPushButton:hover { background-color: #D32F2F; } QPushButton:disabled { background-color: #a0a0a0; }"

        self.add_task_button = QPushButton("Add Task")
        self.add_task_button.clicked.connect(self.add_task)
        self.add_task_button.setFont(QFont("Arial", 10))
        self.add_task_button.setStyleSheet(blue_button_style)
        
        self.edit_task_button = QPushButton("Edit Task")
        self.edit_task_button.clicked.connect(self.edit_task)
        self.edit_task_button.setEnabled(False)
        self.edit_task_button.setFont(QFont("Arial", 10))
        self.edit_task_button.setStyleSheet(blue_button_style)
        
        self.delete_task_button = QPushButton("Delete Task")
        self.delete_task_button.clicked.connect(self.delete_task)
        self.delete_task_button.setEnabled(False)
        self.delete_task_button.setFont(QFont("Arial", 10))
        self.delete_task_button.setStyleSheet(red_button_style)
        
        task_buttons_layout.addWidget(self.add_task_button)
        task_buttons_layout.addWidget(self.edit_task_button)
        task_buttons_layout.addWidget(self.delete_task_button)
        tasks_column_layout.addLayout(task_buttons_layout)

        tasks_and_output_section.addLayout(tasks_column_layout)

        self.task_list_widget.itemSelectionChanged.connect(self.update_task_buttons_state)

        output_column_layout = QVBoxLayout()
        output_column_layout.addWidget(QLabel("<h2>Command Output</h2>"))
        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 10pt;")
        self.output_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        output_column_layout.addWidget(self.output_text_edit)
        
        tasks_and_output_section.addLayout(output_column_layout)
        tasks_and_output_section.setStretch(0, 1)
        tasks_and_output_section.setStretch(1, 2)
        main_layout.addLayout(tasks_and_output_section)

        action_buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Start All Tasks")
        self.start_button.clicked.connect(self.start_all_tasks)
        self.start_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.start_button.setStyleSheet(blue_button_style.replace("padding: 8px", "padding: 10px 20px"))
        
        self.stop_button = QPushButton("Stop Current Task")
        self.stop_button.clicked.connect(self.stop_current_task)
        self.stop_button.setEnabled(False)
        self.stop_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.stop_button.setStyleSheet(blue_button_style.replace("padding: 8px", "padding: 10px 20px"))

        self.report_button = QPushButton("Generate HTML Report")
        self.report_button.clicked.connect(self.generate_html_report)
        self.report_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.report_button.setStyleSheet(blue_button_style.replace("padding: 8px", "padding: 10px 20px"))

        action_buttons_layout.addStretch(1)
        action_buttons_layout.addWidget(self.start_button)
        action_buttons_layout.addWidget(self.stop_button)
        action_buttons_layout.addWidget(self.report_button)
        action_buttons_layout.addStretch(1)
        main_layout.addLayout(action_buttons_layout)

        self.setLayout(main_layout)

    def load_tasks_from_db(self):
        db_tasks = self.db_manager.get_all_tasks()
        self.tasks = []
        for db_task in db_tasks:
            task_id, name, command, description, status, start_time, end_time = db_task
            task = Task(name, command, description, db_id=task_id)
            task.status = status
            self.tasks.append(task)
        self.update_task_list_widget()

    def update_task_buttons_state(self):
        is_selected = len(self.task_list_widget.selectedItems()) > 0
        if not self.current_running_thread or not self.current_running_thread.isRunning():
            self.edit_task_button.setEnabled(is_selected)
            self.delete_task_button.setEnabled(is_selected)
        else:
            self.edit_task_button.setEnabled(False)
            self.delete_task_button.setEnabled(False)

    def add_task(self):
        dialog = NewTaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_task_data()
            task_db_id = self.db_manager.insert_task(data["name"], data["command"], data["description"])
            new_task = Task(data["name"], data["command"], data["description"], db_id=task_db_id)
            self.tasks.append(new_task)
            self.update_task_list_widget()
            self.task_list_widget.scrollToBottom()

    def edit_task(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            return

        selected_row = self.task_list_widget.row(selected_items[0])
        task_to_edit = self.tasks[selected_row]

        dialog = NewTaskDialog(self, task=task_to_edit)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_task_data()
            task_to_edit.name = data["name"]
            task_to_edit.command = data["command"]
            task_to_edit.description = data["description"]
            
            self.db_manager.cursor.execute("UPDATE tasks SET name = ?, command = ?, description = ? WHERE id = ?",
                                          (task_to_edit.name, task_to_edit.command, task_to_edit.description, task_to_edit.db_id))
            self.db_manager.conn.commit()
            self.update_task_list_widget()

    def delete_task(self):
        selected_items = self.task_list_widget.selectedItems()
        if not selected_items:
            return
        
        selected_row = self.task_list_widget.row(selected_items[0])
        task_to_delete = self.tasks[selected_row]
        
        self.db_manager.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_to_delete.db_id,))
        self.db_manager.conn.commit()
        
        del self.tasks[selected_row]
        self.update_task_list_widget()

    def update_task_list_widget(self):
        self.task_list_widget.clear()
        for i, task in enumerate(self.tasks):
            item_text = f"[{i+1}] {task.name}"
            item = QListWidgetItem(item_text)
            
            tooltip_text = f"Command: {task.command}"
            if task.description:
                tooltip_text += f"\nDescription: {task.description}"
            item.setToolTip(tooltip_text)
            
            if task.status == "Running":
                item.setForeground(QColor("#2196F3"))
            elif task.status == "Completed":
                item.setForeground(QColor("#4CAF50"))
            elif task.status == "Error":
                item.setForeground(QColor("#F44336"))
            elif task.status == "Interrupted":
                item.setForeground(QColor("#FF9800"))
            else:
                item.setForeground(QColor("white"))

            self.task_list_widget.addItem(item)
        self.update_task_buttons_state()

    def set_ui_running_state(self, is_running):
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        self.add_task_button.setEnabled(not is_running)
        self.report_button.setEnabled(not is_running)
        self.update_task_buttons_state()

    def start_all_tasks(self):
        if not self.tasks:
            QMessageBox.warning(self, "No Tasks", "Please add tasks before starting.")
            return

        self.output_text_edit.clear()
        self.output_text_edit.append(f"Starting ShellRunner tasks...\n\n") 

        for task in self.tasks:
            self.db_manager.update_task_status(task.db_id, "Pending")
            task.status = "Pending"
        self.update_task_list_widget()

        self.set_ui_running_state(True)
        self.current_task_index = -1
        self.run_next_task()

    def run_next_task(self):
        self.current_task_index += 1
        if self.current_task_index < len(self.tasks):
            current_task = self.tasks[self.current_task_index]
            command_to_execute = current_task.command

            self.db_manager.update_task_status(current_task.db_id, "Running")
            current_task.status = "Running"
            self.update_task_list_widget()

            self.current_running_thread = CommandRunner(command_to_execute, self.current_task_index, current_task.db_id)
            self.current_running_thread.output_signal.connect(self.update_output_text)
            self.current_running_thread.log_to_db_signal.connect(self.db_manager.insert_log)
            self.current_running_thread.command_finished_signal.connect(self.on_command_finished)
            self.current_running_thread.start()
        else:
            self.output_text_edit.append("\n" + "="*70 + "\n")
            self.output_text_edit.append("[✓] All tasks completed!\n")
            self.output_text_edit.append("="*70 + "\n")
            self.set_ui_running_state(False)
            self.current_task_index = -1
            self.current_running_thread = None

    def stop_current_task(self):
        if self.current_running_thread and self.current_running_thread.isRunning():
            self.current_running_thread.stop_execution()
        else:
            self.output_text_edit.append("[!] No task is currently running to stop.\n")

    def update_output_text(self, text):
        self.output_text_edit.insertPlainText(text)
        self.output_text_edit.verticalScrollBar().setValue(self.output_text_edit.verticalScrollBar().maximum()) 

    def on_command_finished(self, task_index, result_message):
        if 0 <= task_index < len(self.tasks):
            task = self.tasks[task_index]
            if "Completed" in result_message:
                task.status = "Completed"
            elif "Interrupted" in result_message:
                task.status = "Interrupted"
            elif "Error" in result_message:
                task.status = "Error"
            else:
                task.status = "Completed"
            
            self.db_manager.update_task_status(task.db_id, task.status)
            self.update_task_list_widget()

        if "Interrupted" in result_message:
            self.output_text_edit.append("\n[!] Task sequence interrupted by user. Stopping automation.\n")
            self.set_ui_running_state(False)
            self.current_task_index = -1
            self.current_running_thread = None
        else:
            self.run_next_task()

    def generate_html_report(self):
        all_tasks_data = self.db_manager.get_all_tasks()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ShellRunner Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
                .container { max-width: 1000px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
                h1 { color: #2196F3; text-align: center; }
                h2 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 30px; }
                .task-section { background-color: #e9e9e9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
                .task-title { font-weight: bold; font-size: 1.1em; color: #0056b3; }
                .task-status { padding: 5px 10px; border-radius: 3px; font-weight: bold; }
                .status-Completed { background-color: #d4edda; color: #155724; }
                .status-Error { background-color: #f8d7da; color: #721c24; }
                .status-Interrupted { background-color: #fff3cd; color: #856404; }
                .status-Pending { background-color: #e2e3e5; color: #383d41; }
                .status-Running { background-color: #cce5ff; color: #004085; }
                pre { background-color: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
                .info-label { font-weight: bold; }
                .info-value { margin-left: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ShellRunner Automation Report</h1>
                <p style="text-align: center;">Generated on: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        """

        if not all_tasks_data:
            html_content += "<p style='text-align: center;'>No tasks found in the database to generate a report.</p>"
        else:
            for task_data in all_tasks_data:
                task_id, name, command, description, status, start_time, end_time = task_data
                
                logs = self.db_manager.get_task_logs(task_id)
                log_output = "\n".join([f"{ts} - {line}" for ts, line in logs])

                html_content += f"""
                <div class="task-section">
                    <div class="task-header">
                        <span class="task-title">{name}</span>
                        <span class="task-status status-{status}">{status}</span>
                    </div>
                    <div><span class="info-label">Command:</span><span class="info-value">{command}</span></div>
                    <div><span class="info-label">Description:</span><span class="info-value">{description if description else 'N/A'}</span></div>
                    <div><span class="info-label">Start Time:</span><span class="info-value">{start_time if start_time else 'N/A'}</span></div>
                    <div><span class="info-label">End Time:</span><span class="info-value">{end_time if end_time else 'N/A'}</span></div>
                    <h3>Output:</h3>
                    <pre>{log_output}</pre>
                </div>
                """
        
        html_content += """
            </div>
        </body>
        </html>
        """

        report_filename = datetime.datetime.now().strftime("shellrunner_report_%Y%m%d_%H%M%S.html")
        report_path = os.path.join(self.reports_dir, report_filename)

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            QMessageBox.information(self, "Report Generated", f"HTML report saved as: {report_path}")
            
            try:
                os.startfile(report_path)
            except AttributeError:
                subprocess.Popen(['xdg-open', report_path])
            except Exception as e:
                QMessageBox.warning(self, "Open Report", f"Could not open report automatically: {e}\nPlease open '{report_path}' manually.")

        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report: {e}")

    def closeEvent(self, event):
        self.db_manager.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    ex = ShellRunnerApp()
    ex.show()
    sys.exit(app.exec_())
