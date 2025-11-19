import curses
from datetime import datetime
import matplotlib.pyplot as plt
import duckdb
import os
import requests
import json

class MoodTrackerCLI:
    def __init__(self, stdscr, db_path="poems.db"):
        self.stdscr = stdscr
        self.dates = []
        self.moods = []
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.db_path = db_path
        
        curses.start_color()
        # White text on blue background
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Yellow text on blue background for inspirations
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLUE)
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.clear()
        
        self.run()
    
    def get_input(self, y, x, max_length=100):
        """Get user input at specified coordinates"""
        curses.echo()
        curses.curs_set(1)
        self.stdscr.move(y, x)
        input_str = ""
        while len(input_str) < max_length:
            char = self.stdscr.getch()
            if char == 10 or char == 13:  # Enter key
                break
            elif char == 127 or char == 8:  # Backspace
                if len(input_str) > 0:
                    input_str = input_str[:-1]
                    self.stdscr.addstr(y, x + len(input_str), ' ')
                    self.stdscr.move(y, x + len(input_str))
            elif 32 <= char <= 126:  # Printable ASCII
                input_str += chr(char)
        curses.noecho()
        curses.curs_set(0)
        return input_str
    
    def get_poem_by_mood(self, mood_score):
        """
        Get a random poem from the database based on mood score.
        If mood >= 6, return a 'happy' poem. If mood <= 5, return a 'sad' poem.
        
        Returns:
            dict with 'poem_name', 'writer_name', 'poem_text' or None if not found
        """
        if not os.path.exists(self.db_path):
            return None
        
        try:
            conn = duckdb.connect(self.db_path)
            
            # Determine mood_type based on score
            mood_type = "happy" if mood_score >= 6 else "sad"
            
            # Get a random poem with the matching mood_type
            result = conn.execute("""
                SELECT poem_name, writer_name, poem_text
                FROM poems
                WHERE mood_type = ?
                ORDER BY RANDOM()
                LIMIT 1
            """, [mood_type]).fetchone()
            
            conn.close()
            
            if result:
                return {
                    "poem_name": result[0],
                    "writer_name": result[1],
                    "poem_text": result[2]
                }
            else:
                return None
        except Exception as e:
            # If there's an error, return None
            return None
    
    def display_poem(self, poem, start_line, max_lines=5, separator_length=50):

        # Main function for CPT

        # If no poem is found, display a message and return the next line
        if poem is None:
            self.stdscr.addstr(start_line, 1, "No poem found in database for this mood.", curses.color_pair(1))
            return start_line + 1
        
        # Display a line of separators
        separator = "-" * separator_length
        self.stdscr.addstr(start_line, 1, separator, curses.color_pair(1))
        
        # Display poem title
        title_line = start_line + 1
        self.stdscr.addstr(title_line, 1, f"Poem: {poem['poem_name']}", curses.color_pair(1))
        
        # Display writer name
        writer_line = start_line + 2
        self.stdscr.addstr(writer_line, 1, f"By: {poem['writer_name']}", curses.color_pair(1))
        
        # Empty line for spacing
        empty_line = start_line + 3
        self.stdscr.addstr(empty_line, 1, "", curses.color_pair(1))
        
        # Display poem text lines with character-by-character animation
        poem_text = poem.get('poem_text', '')
        poem_lines = poem_text.split('\n') if poem_text else []
        
        current_line = start_line + 4
        max_width = curses.COLS - 2
        lines_displayed = 0
        
        # Loop through poem lines
        for poem_line in poem_lines:
            # Have we reached the maximum number of lines?
            if lines_displayed >= max_lines:
                break
            
            # Do we have enough screen space?
            if current_line >= curses.LINES - 2:
                break
            
            # Handle line length; truncate if too long
            display_line = poem_line
            if len(poem_line) > max_width:
                display_line = poem_line[:max_width - 3] + "..."
            
            # Display line character by character (typewriter effect)
            x_pos = 1
            for char in display_line:
                self.stdscr.addstr(current_line, x_pos, char, curses.color_pair(1))
                self.stdscr.refresh()
                curses.napms(50)  # 50ms delay between characters
                x_pos += 1
            
            current_line += 1
            lines_displayed += 1
        
        return current_line
    
    def draw_main_menu(self):
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Mood Tracker", curses.A_BOLD | curses.color_pair(1))
        self.stdscr.addstr(3, 1, "1. Add mood record", curses.color_pair(1))
        self.stdscr.addstr(4, 1, "2. View mood records", curses.color_pair(1))
        self.stdscr.addstr(5, 1, "3. View mood chart", curses.color_pair(1))
        self.stdscr.addstr(6, 1, "4. Inspirations", curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(7, 1, "5. Exit", curses.color_pair(1))
        self.stdscr.addstr(9, 1, "Please choose an option (1-5): ", curses.color_pair(1))
        self.stdscr.refresh()

    def add_mood_record(self):
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Enter Date (YYYY-MM-DD):", curses.color_pair(1))
        self.stdscr.addstr(2, 1, f"Current date: {self.current_date}", curses.color_pair(1))
        self.stdscr.addstr(3, 1, "Date: ", curses.color_pair(1))
        self.stdscr.refresh()
        date_input = self.get_input(3, 7, max_length=10)
        if not date_input:
            date_input = self.current_date  # Default to current date
        
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Enter mood score (1-10):", curses.color_pair(1))
        self.stdscr.addstr(2, 1, "Score: ", curses.color_pair(1))
        self.stdscr.refresh()
        mood_input = self.get_input(2, 8, max_length=2)

        try:
            mood_score = int(mood_input)
            if 1 <= mood_score <= 10:
                self.dates.append(date_input)
                self.moods.append(mood_score)
                self.stdscr.addstr(4, 1, f"Record added: {date_input} - Mood: {mood_score}", curses.color_pair(1))
                
                # Get and display a poem based on mood
                poem = self.get_poem_by_mood(mood_score)
                line_offset = 6
                
                # Display poem using the structured function
                last_poem_line = self.display_poem(poem, line_offset, max_lines=5, separator_length=50)
                
                # Check for consecutive days with low or high mood scores
                self.check_mood_trends(last_poem_line + 1)

            else:
                self.stdscr.addstr(4, 1, "Invalid mood score! Must be between 1 and 10.", curses.color_pair(1))
        except ValueError:
            self.stdscr.addstr(4, 1, "Invalid input! Please enter a number for the mood score.", curses.color_pair(1))
        self.stdscr.refresh()
        self.stdscr.getch()  # Wait for a key press

    def check_mood_trends(self, start_line=5):
        # If there are at least 3 mood records
        if len(self.moods) >= 3:
            # Check the last 3 moods
            last_three_moods = self.moods[-3:]

            # Check if the last 3 moods are all below 5 (low mood) or above 5 (high mood)
            if all(mood < 5 for mood in last_three_moods):
                self.stdscr.addstr(start_line, 1, "You've had three consecutive low moods. Consider reflecting on your feelings.", curses.color_pair(1))
            elif all(mood > 5 for mood in last_three_moods):
                self.stdscr.addstr(start_line, 1, "You've had three consecutive high moods. Great job staying positive!", curses.color_pair(1))
        self.stdscr.refresh()

    def view_mood_records(self):
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Mood Records:", curses.color_pair(1))
        if not self.dates:
            self.stdscr.addstr(3, 1, "No records to display.", curses.color_pair(1))
        else:
            for idx, (date, mood) in enumerate(zip(self.dates, self.moods)):
                self.stdscr.addstr(3 + idx, 1, f"{date} - Mood: {mood}", curses.color_pair(1))
        self.stdscr.refresh()
        self.stdscr.getch()

    def plot_mood_chart(self):
        if not self.dates or not self.moods:
            self.stdscr.clear()
            self.stdscr.bkgd(' ', curses.color_pair(1))
            self.stdscr.addstr(1, 1, "No records to display!", curses.color_pair(1))
            self.stdscr.refresh()
            self.stdscr.getch()
            return

        # Sort dates and moods by date
        sorted_dates_moods = sorted(zip(self.dates, self.moods), key=lambda x: x[0])
        sorted_dates, sorted_moods = zip(*sorted_dates_moods)

        # Plotting the mood chart
        plt.figure(figsize=(10, 5))
        plt.plot(sorted_dates, sorted_moods, marker='o', linestyle='-', color='b')
        plt.xlabel('Date')
        plt.ylabel('Mood Score (1-10)')
        plt.title('Mood Tracker Over Time')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def get_random_poem(self):
        """
        Fetch a random poem from PoetryDB API with less than 1000 lines.
        Keeps querying until a suitable poem is found.
        
        Returns:
            dict with 'title', 'author', 'lines' or None if error
        """
        max_attempts = 20  # Prevent infinite loops
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = requests.get("https://poetrydb.org/random", timeout=5)
                response.raise_for_status()
                poems = response.json()
                
                if poems and len(poems) > 0:
                    poem = poems[0]
                    linecount = int(poem.get('linecount', 0))
                    
                    # Check if poem has less than 1000 lines
                    if linecount < 1000:
                        return {
                            'title': poem.get('title', 'Untitled'),
                            'author': poem.get('author', 'Unknown'),
                            'lines': poem.get('lines', [])
                        }
                
                attempts += 1
            except (requests.RequestException, json.JSONDecodeError, ValueError, KeyError) as e:
                attempts += 1
                if attempts >= max_attempts:
                    return None
        
        return None
    
    def display_inspiration_poem(self, poem, start_line, separator_length=50):
        """
        Display an inspiration poem from the API.
        
        Args:
            poem: dict with 'title', 'author', 'lines'
            start_line: starting line number for display
            separator_length: length of separator line
        """
        if poem is None:
            self.stdscr.addstr(start_line, 1, "Unable to fetch poem. Please try again later.", curses.color_pair(1))
            return start_line + 1
        
        # Display a line of separators
        separator = "-" * separator_length
        self.stdscr.addstr(start_line, 1, separator, curses.color_pair(1))
        
        # Display poem title
        title_line = start_line + 1
        self.stdscr.addstr(title_line, 1, f"Poem: {poem['title']}", curses.color_pair(1))
        
        # Display author name
        author_line = start_line + 2
        self.stdscr.addstr(author_line, 1, f"By: {poem['author']}", curses.color_pair(1))
        
        # Empty line for spacing
        empty_line = start_line + 3
        self.stdscr.addstr(empty_line, 1, "", curses.color_pair(1))
        
        # Display poem lines with character-by-character animation
        poem_lines = poem.get('lines', [])
        current_line = start_line + 4
        max_width = curses.COLS - 2
        
        # Loop through poem lines
        for poem_line in poem_lines:
            # Do we have enough screen space?
            if current_line >= curses.LINES - 2:
                break
            
            # Handle line length; truncate if too long
            display_line = poem_line
            if len(poem_line) > max_width:
                display_line = poem_line[:max_width - 3] + "..."
            
            # Display line character by character (typewriter effect)
            x_pos = 1
            for char in display_line:
                self.stdscr.addstr(current_line, x_pos, char, curses.color_pair(1))
                self.stdscr.refresh()
                curses.napms(50)  # 50ms delay between characters
                x_pos += 1
            
            current_line += 1
        
        return current_line
    
    def show_inspirations(self):
        """Display a random inspiration poem from PoetryDB"""
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Fetching inspiration...", curses.color_pair(1))
        self.stdscr.refresh()
        
        poem = self.get_random_poem()
        
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.addstr(1, 1, "Inspirations", curses.A_BOLD | curses.color_pair(1))
        
        line_offset = 3
        last_line = self.display_inspiration_poem(poem, line_offset, separator_length=50)
        
        # Add instruction to press any key
        self.stdscr.addstr(last_line + 1, 1, "Press any key to return to menu...", curses.color_pair(1))
        self.stdscr.refresh()
        self.stdscr.getch()

    def run(self):
        while True:
            self.draw_main_menu()

            choice = self.stdscr.getch()

            if choice == ord('1'):
                self.add_mood_record()
            elif choice == ord('2'):
                self.view_mood_records()
            elif choice == ord('3'):
                self.plot_mood_chart()
            elif choice == ord('4'):
                self.show_inspirations()
            elif choice == ord('5'):
                break  # Exit the program
            else:
                self.stdscr.clear()
                self.stdscr.bkgd(' ', curses.color_pair(1))
                self.stdscr.addstr(1, 1, "Invalid choice! Please choose a valid option (1-5).", curses.color_pair(1))
                self.stdscr.refresh()
                self.stdscr.getch()

def main(stdscr):
    mood_tracker = MoodTrackerCLI(stdscr)

if __name__ == "__main__":
    curses.wrapper(main)
