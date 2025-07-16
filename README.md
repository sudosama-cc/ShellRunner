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

The application screen will open

![ShellRunner](https://i.imgur.com/Rw2fNgm.png)

After launching the application:

**Add Tasks:** Click the "Add Task" button to define new tasks (task name, command, description)

![ShellRunner](https://i.imgur.com/rSZi2eH.png)

For example, I automated the Fuzzing process by adding the tools in the image.

![ShellRunner](https://i.imgur.com/f4DMDMn.png)

**Start Automation:** Click the "Start All Tasks" button to begin executing all tasks in the list sequentially.

![ShellRunner](https://i.imgur.com/hwlZiIh.png)

**Generate Report:** After all tasks are complete, or at any time you wish, click the "Generate HTML Report" button to create a detailed HTML report. The report will be automatically saved to the `reports/` directory and opened.

![ShellRunner](https://i.imgur.com/JzM0QcR.png)
