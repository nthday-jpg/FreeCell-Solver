# FreeCell Solver

This project is a Python-based application designed to solve FreeCell solitaire deals using various search algorithms. It features a graphical interface for visualization and a suite of experiments for benchmarking algorithm performance.

## Prerequisites

Before running the solver, ensure you have Python installed. This project relies on several external libraries for its GUI and data processing:
* **pygame**: Used for the graphical user interface.
* **matplotlib**: Required for plotting and visualizing experiment results.
* **numpy**: Handles numerical operations and state management.

## Installation

1.  **Clone or Download**: Save the project files to your local machine.
2.  **Navigate**: Open your terminal or command prompt and go to the project's root directory.
3.  **Install Dependencies**: Execute the following command to install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
   

## How to Run

To launch the solver, run the primary script from the root directory:

```bash
python main.py
```


### **Execution Details:**
* **Path Configuration**: The script automatically adds the `src` directory to the system path, ensuring that all internal modules are correctly resolved during execution.
* **Application Launch**: The entry point triggers the `run()` function within the GUI package to initialize the window and start the solver interface.

## Project Structure

* **main.py**: The central entry point for the application.
* **src/freecell**: Contains the core logic, including algorithm implementations (A*, BFS, DFS, UCS, IDS) and the GUI components.
* **requirements.txt**: Lists all necessary Python dependencies and their versions.

## Features
* **Multiple Solvers**: Supports a variety of AI search strategies to solve FreeCell deals.
* **GUI Integration**: A visual interface to interact with the game and observe the solver in action.
* **Performance Benchmarking**: Included experiments to track metrics like expansion count and time efficiency across different algorithms.