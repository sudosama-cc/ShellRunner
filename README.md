# ShellRunner: Advanced Command Automation Tool

ShellRunner is a modern and user-friendly GUI application designed to automate multiple shell commands sequentially. Easily manage your tasks, monitor outputs in real-time, and automatically generate detailed HTML reports of all your operations.

![ShellRunner Screenshot](https://via.placeholder.com/800x450?text=ShellRunner+Screenshot) ---

## Features

* **Intuitive Task Management:** Easily add, edit, and delete tasks.
* **Sequential Command Execution:** Run tasks automatically in the order you define.
* **Real-Time Output Monitoring:** View the live output of running commands directly within the application interface.
* **Persistent Per-Task Logging:** All output for each task, along with timestamps, is stored in a local SQLite database. Your logs remain safe even if the application is closed.
* **Detailed HTML Reports:** Generate professional HTML reports summarizing the entire automation process, including each task's command, status, and full logs. Reports are saved in the `reports/` directory.
* **Organized File Structure:** Database files are kept in `db/`, and reports in `reports/` for neat organization.

---

## Installation

To set up and run ShellRunner on your local system, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/ShellRunner.git](https://github.com/YOUR_USERNAME/ShellRunner.git)
    cd ShellRunner
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

After launching the application:

1.  **Add Tasks:** Click the "Add Task" button to define new tasks (task name, command, description).
2.  **Manage Tasks:** Select existing tasks to "Edit Task" or "Delete Task".
3.  **Start Automation:** Click the "Start All Tasks" button to begin executing all tasks in the list sequentially.
4.  **Stop Automation:** Use the "Stop Current Task" button to halt the currently running task.
5.  **Generate Report:** After all tasks are complete, or at any time you wish, click the "Generate HTML Report" button to create a detailed HTML report. The report will be automatically saved to the `reports/` directory and opened.

---

## File Structure
