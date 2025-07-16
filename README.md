# ShellRunner: Advanced Command Automation Tool

ShellRunner is a modern and user-friendly GUI application designed to automate multiple shell commands sequentially. Easily manage your tasks, monitor outputs in real-time, and automatically generate detailed HTML reports of all your operations.

## Purpose of ShellRunner & Target Audience

ShellRunner was developed to streamline and automate repetitive command-line tasks that are often part of larger workflows. Instead of manually executing commands one by one, users can define a sequence of tasks, run them efficiently, and maintain a clear record of the entire process.

This tool is particularly useful for:

Cybersecurity Professionals / Penetration Testers: For automating reconnaissance steps (e.g., nmap scans, dirb enumeration), post-exploitation activities, or setting up test environments.

System Administrators / DevOps Engineers: To automate routine server maintenance, deployment scripts, log analysis, or repetitive configuration tasks across multiple systems.

Developers: For automating build processes, running multiple test suites, setting up development environments, or managing project dependencies.

Researchers / Data Scientists: To automate data collection, pre-processing steps, or running sequential analysis scripts.

Anyone needing to automate command-line workflows: If you find yourself repeatedly typing the same sequence of commands into a terminal, ShellRunner can save you significant time and reduce manual errors.

ShellRunner aims to provide a reliable, transparent, and easy-to-use solution for automating command execution, complete with detailed historical reports for review and auditing.

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

**Generate Report:** After all tasks are complete, or at any time you wish, click the "Generate HTML Report" button to create a detailed HTML report. The report will be automatically saved to the `reports/`  directory and opened.

![ShellRunner](https://i.imgur.com/JzM0QcR.png)

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
