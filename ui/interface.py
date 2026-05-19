import json

class CLIInterface:
    def __init__(self, facts_path):
        """
        Initializes the User Interface.
        Loads available facts (symptoms) to present to the user.
        """
        with open(facts_path, 'r', encoding='utf-8') as f:
            self.facts = json.load(f)
            
    def get_user_symptoms(self):
        """
        Displays a list of symptoms and collects user input.
        Returns a set of selected fact IDs.
        """
        print("\n--- Computer Troubleshooting Expert System ---")
        print("Please select the symptoms you are experiencing:")
        print("----------------------------------------------")
        
        for i, fact in enumerate(self.facts):
            print(f"{i + 1}. {fact['description']}")
            
        print("----------------------------------------------")
        user_input = input("Enter the numbers corresponding to your symptoms (comma-separated, e.g., 1,3,4): ")
        
        selected_facts = set()
        if user_input.strip():
            choices = [c.strip() for c in user_input.split(',')]
            for choice in choices:
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(self.facts):
                        selected_facts.add(self.facts[idx]['id'])
                        
        return selected_facts
        
    def display_results(self, explanation_text):
        """
        Displays the final diagnosis and explanation trace.
        """
        print("\n================ DIAGNOSIS RESULTS ================")
        print(explanation_text)
        print("===================================================\n")
