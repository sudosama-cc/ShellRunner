# ShellRunner: Advanced Command Automation Tool

ShellRunner is a modern and user-friendly GUI application designed to automate multiple shell commands sequentially. Easily manage your tasks, monitor outputs in real-time, and automatically generate detailed HTML reports of all your operations.

## Installation

To set up and run ShellRunner on your local system, follow these steps:

 ```bash
    git clone https://github.com/sudosama-cc/ShellRunner.git

    cd ShellRunner
    
    pip install -r requirements.txt
 ```

## Usage

Start the application

```bash
python3 ShellRunner.py
```

The Application screen will open

![ShellRunner](https://i.imgur.com/Rw2fNgm.png)

After launching the application:

1.  **Add Tasks:** Click the "Add Task" button to define new tasks (task name, command, description)
2.  ![ShellRunner](https://i.imgur.com/rSZi2eH.png)
  
5.  **Manage Tasks:** Select existing tasks to "Edit Task" or "Delete Task".
6.  **Start Automation:** Click the "Start All Tasks" button to begin executing all tasks in the list sequentially.
7.  **Stop Automation:** Use the "Stop Current Task" button to halt the currently running task.
8.  **Generate Report:** After all tasks are complete, or at any time you wish, click the "Generate HTML Report" button to create a detailed HTML report. The report will be automatically saved to the `reports/` directory and opened.
