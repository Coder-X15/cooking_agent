# Cooking Agent

## What This Is
This is a simple cooking agent that can be used to help you cook different dishes. It hasn't been given multimodal response capabilities, but I have tried my best to prompt engineer it to some extent of functionality (To be 100% honest, I haven't tried all the possible chat instances).

To chat with this agent I have built a simple chat interface with Flask.

## How to Use This
### Prerequisites:
Have your Gemini developer API key and Spoonacular API key ready in a file named `.env`, in this format:
```
GOOGLE_API_KEY="<key>"
SPOONACULAR_KEY="<key>"
```
1. Clone this repo
2. `cd` into the repo and `pip install -r requirements.txt`
3. `python app.py` to start the server
4. Open a web browser and navigate to `http://localhost:5000/`.

## TODO:
1. Develop a Flask frontend for testers to interface with