from flask import Flask, render_template, request, redirect, url_for
from agent.global_agent import *
import markdown


# first we need to create a child class out of the AIAgent class to enable proper functionality
class Agent(AIAgent):

    def __init__(self):
        super().__init__()

    # we'll just have to overwrite the run function to run once and return a reply dialogue.
    def run(self, user_input : str):
        intent = self.getIntent(user_input)
        if 'None' in intent.text:
            return {'assistant':self.handleNoneIntent()}
        else:
            # the output comes as a text repr. of a JSON/Python dictionary
            # we need to convert it first
            output = intent.text
            return {'assistant':self.handleFetchRecipe(output)}
        

# building the Flask app
app = Flask(__name__)
app.config['debug'] = True

# creating the agent
agent = Agent()

# conversation as a list
conversation = []

@app.route('/')
def index():
    return render_template('chatpage.html', messages = conversation)

@app.route('/consume_message', methods=['POST', 'GET'])
def chat():
    if request.method == "POST":
        user_input = request.form.get('user_message')
        # add the user dialogue to the conversation history
        conversation.append({'user':user_input})
        
        # get the agent output
        output = agent.run(user_input)

        #modify the output to HTML syntax
        output['assistant'] = markdown.markdown(output['assistant'])
        
        conversation.append(output)
        return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)