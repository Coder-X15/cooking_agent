# Cooking Agent

## What This Is
This is a simple cooking agent that can be used to help you cook different dishes. It hasn't been given multimodal response capabilities, but I have tried my best to prompt engineer it to some extent of functionality (To be 100% honest, I haven't tried all the possible chat instances).

To chat with this agent I have built a simple chat interface with Flask.

## Pros
- A reusable backend based on Flask
- A minimal chat interface
- A simple cooking agent that can be used to help you cook different dishes

## Cons
- Often getting out of hand
- Not all dishes can be found out (however, Gemini 2.0 Flash-001 may be able to generate some by itself) [FEATURE SUGGESTION]
- Pretty simple in terms of development complexity.
 
### Prerequisites:
Have your Gemini developer API key and Spoonacular API key ready in a file named `.env`, in this format:
```
GOOGLE_API_KEY="<key>"
SPOONACULAR_KEY="<key>"
```
Save it in the `agent` folder of the repo once cloned.
1. Clone this repo
2. `cd` into the repo and `pip install -r requirements.txt`
3. `python app.py` or `flask run` to start the server
4. Open a web browser and navigate to `http://localhost:5000/`.

## TODO:
1. Need to refine the logic in a better way.
2. Need to get the model to respond within context.

