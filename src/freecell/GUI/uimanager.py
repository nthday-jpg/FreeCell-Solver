import tkinter as tk
from tkinter import ttk

class FreecellSolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Freecell AI Solver Visualizer")
        self.root.geometry("1000x700")
        self.root.configure(padx=10, pady=10)

        # --- State Variables ---
        self.is_playing = False
        self.current_step = 0
        self.playback_speed_ms = 500  # Half a second per move
        self.solution_moves = []      # Will eventually hold your list of Move objects

        # --- Build the UI ---
        self._build_ui()

    def _build_ui(self):
        # 1. Main Layout: PanedWindow to split Canvas and Controls
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # 2. Left Side: The Game Canvas (A nice felt green)
        self.canvas = tk.Canvas(main_pane, bg="#2E8B57", highlightthickness=0)
        main_pane.add(self.canvas, weight=4) # Canvas takes up 80% of width

        # 3. Right Side: The Control Panel
        control_frame = ttk.Frame(main_pane, padding=10)
        main_pane.add(control_frame, weight=1)

        # --- Control Panel Widgets ---
        ttk.Label(control_frame, text="Solver Settings", font=("Arial", 14, "bold")).pack(pady=(0, 15))

        # Algorithm Dropdown
        ttk.Label(control_frame, text="Search Algorithm:").pack(anchor=tk.W)
        self.algo_var = tk.StringVar(value="A* Search")
        self.algo_dropdown = ttk.Combobox(control_frame, textvariable=self.algo_var, state="readonly")
        self.algo_dropdown['values'] = ("Breadth-First Search (BFS)", "Depth-First Search (DFS)", "A* Search")
        self.algo_dropdown.pack(fill=tk.X, pady=(0, 20))

        # Action Buttons
        self.btn_solve = ttk.Button(control_frame, text="1. Run Solver", command=self.run_solver)
        self.btn_solve.pack(fill=tk.X, pady=5)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        self.btn_play = ttk.Button(control_frame, text="Play / Pause", command=self.toggle_playback)
        self.btn_play.pack(fill=tk.X, pady=5)

        self.btn_step = ttk.Button(control_frame, text="Step Forward", command=self.step_forward)
        self.btn_step.pack(fill=tk.X, pady=5)

        self.btn_reset = ttk.Button(control_frame, text="Reset Board", command=self.reset_board)
        self.btn_reset.pack(fill=tk.X, pady=5)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Waiting for initialization...")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, wraplength=150)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=20)

        # Draw the initial empty/dummy board
        self.draw_board()

    # --- Logic & Controller Functions ---

    def run_solver(self):
        """Simulates running your AI search algorithm."""
        algo = self.algo_var.get()
        self.status_var.set(f"Status: Running {algo}...\n(Check console)")
        print(f"--- Firing up {algo} ---")
        
        # TODO: Hook up your actual GameState.initial() and search algorithm here
        # For now, we simulate finding a solution of 10 dummy moves
        self.solution_moves = ["Move 1", "Move 2", "Move 3", "Move 4", "Move 5"]
        self.current_step = 0
        
        self.status_var.set(f"Status: Solution found! ({len(self.solution_moves)} moves)")
        print("Solution loaded. Ready to play.")

    def toggle_playback(self):
        """Starts or pauses the automatic playback."""
        if not self.solution_moves:
            print("Please run the solver first!")
            return

        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.status_var.set("Status: PLAYING")
            print("Playback started...")
            self.playback_loop()
        else:
            self.status_var.set("Status: PAUSED")
            print("Playback paused.")

    def playback_loop(self):
        """The timer loop that plays moves automatically."""
        if self.is_playing:
            self.step_forward()
            
            # If we haven't reached the end, schedule the next tick
            if self.current_step < len(self.solution_moves):
                self.root.after(self.playback_speed_ms, self.playback_loop)
            else:
                self.is_playing = False
                self.status_var.set("Status: FINISHED")
                print("End of solution reached.")

    def step_forward(self):
        """Applies the next move and redraws the board."""
        if self.current_step < len(self.solution_moves):
            move = self.solution_moves[self.current_step]
            print(f"Applying step {self.current_step + 1}: {move}")
            
            # TODO: current_game = current_game.apply_move(move)
            
            self.current_step += 1
            self.draw_board() # Redraw the canvas with the new state
        else:
            print("No more moves to apply.")

    def reset_board(self):
        """Stops playback and resets to the initial state."""
        self.is_playing = False
        self.current_step = 0
        self.solution_moves = []
        self.status_var.set("Status: Board Reset.")
        print("Board reset to initial state.")
        self.draw_board()

    # --- View Functions (Step 2 Preview) ---

    def draw_board(self):
        """Clears the canvas and draws the current GameState."""
        self.canvas.delete("all") # Wipe the slate clean
        
        # DUMMY DRAWING FOR STEP 1: Just showing that the canvas updates
        self.canvas.create_text(
            400, 300, 
            text=f"Game Board Visuals Go Here\nCurrent Step: {self.current_step}", 
            fill="white", 
            font=("Arial", 24),
            justify=tk.CENTER
        )
        
        # Draw a little moving circle to prove the step is working
        x_offset = self.current_step * 50
        self.canvas.create_oval(100 + x_offset, 100, 150 + x_offset, 150, fill="yellow")

# --- Application Entry Point ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FreecellSolverApp(root)
    root.mainloop()