# build ref: https://github.com/googleapis/python-genai
# reference for prompting system prompting: https://github.com/googleapis/python-genai#system-instructions-and-other-configs


from google import genai
from google.genai import types
import spoonacular as sp
import dotenv
import os
import json

# laoding environement configs
dotenv.load_dotenv()

class AIAgent:

    def __init__(self):
        # loading the chat client
        # Agent structure:
        # 1. Main chat agent: involves in interaction with the user
        # 2. Recipe fetcher function/ tool: fetches the required recipe(s) from allrecipes.com
        # Agent working:
        # - Identify intent. 
        # - Branch 1: If the intent is to help the person cook or to simply fetch a recipe, call the agent with the tool.
        # - Branch 2: For a None intent, chat as usual

        # context switch
        self.is_contextual = False

        # Gemini chat client
        self.client = genai.Client(
            api_key=os.environ['GOOGLE_API_KEY'],
            http_options=types.HttpOptions(api_version='v1alpha')
        )

        # Spoonacular API client
        self.sp_api = sp.API(api_key=os.environ['SPOONACULAR_KEY'])

        self.model = 'gemini-2.0-flash-001'

        # specific prompts
        self.intent_prompt = '''Identify the user intent (either to fetch a recipe, or a "None" intent). If the user intends to get a recipe,
        print "Fetch the recipe for <name of the dish with every letter in lower-case and seperated by underscores>", otherwise print "None". Note that every
        dialogue is not an intent to fetch the recipe. Dialogues like exclamations (eg.: "Ah! Those sizzling bagels!") are to be considered as "None" intent. '''

        self.none_prompt = ['''Converse with the user almost like how a normal human user would. Be suggestive when it comes to ideas,
        ask opinions subtly (like "Ain't that so?", "What do you think", etc.). Hide as much of your bot behaviour as you can.''']

        # recipe fetcher function call declaration
        self.fetch_recipe_tool_decl = types.FunctionDeclaration(
            name = 'fetch_recipe',
            description = "Fetch the recipe for a specific item",
            parameters = types.Schema(
                type = 'OBJECT',
                properties = {
                    'item': types.Schema(
                        type = 'STRING',
                        description = 'The bakery item/beverage you want to make'
                    )
                },
                required = ['item']
            )
        )
        self.fetch_recipe_tool = types.Tool(function_declarations= [self.fetch_recipe_tool_decl])

        # system memory to hold the conversation done so far
        self.system_memory = []

    def getIntent(self, user_input : str):
        # get the intent from the user input

        # add the user input to the system memory
        self.system_memory.append(
            types.Content(
                role = 'user',
                parts = [types.Part.from_text(text = user_input)]
            )
        )

        # return the intent
        return self.client.models.generate_content(model = self.model, 
                                                   contents = [self.system_memory[-1]],
                                                   config = types.GenerateContentConfig(
                                                       system_instruction= self.intent_prompt,
                                                       max_output_tokens= 25,
                                                       temperature= 0.2
                                                    )
                                                )
    
    def handleFetchRecipe(self, query : str):
        # fetches the recipe and changes the chat mode into a cooking guide

        # fetch a function call part
        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(tools=[self.fetch_recipe_tool]),
        )

        function_call_part = response.function_calls[0]
        function_call_content = response.candidates[0].content
        recipe = None

        try:
            print("Getting the recipe...") # debug line 1
            # parse the function call to get the item name
            item_name = function_call_part.args['item']

            # get the recipe for the item
            recipe = self.fetchRecipe(item_name)
            function_response = {'result': recipe}
        except:
            # raise an exception
            raise Exception("Failed to get the recipe for the item")
        
        if not self.is_contextual:

            # if the chat mode hasn't been switched to contextual, do it
            self.is_contextual = True

            # define a working prompt
            working_prompt = '''Guide the user, step-by-step, through the recipe. Do list the quantity 
            when you list ingredients. Wait when the user gives signs for you to pause. Once the whole recipe has been 
            done or the user doesn't seems to have decided not to cook anything, return "Done".'''

            # add the working prompt to the none_prompt variable to be called during the handling of the None prompt
            self.none_prompt.append(working_prompt)

        # define the conversational objects to be added to the current chat history
        user_prompt_content = types.Content(
            role = 'user',
            parts = [
                types.Part.from_text(text = query)
            ]
        )

        function_response_part = types.Part.from_function_response(
            name=function_call_part.name,
            response= function_response,
        )

        function_response_content = types.Content(
            role='tool', parts=[function_response_part]
        )

        self.system_memory += [
                user_prompt_content,
                function_call_content,
                function_response_content,
            ]
        
        response = self.client.models.generate_content(
            model=self.model,
            contents= self.system_memory,
            config=types.GenerateContentConfig(
                tools=[self.fetch_recipe_tool],
                system_instruction= self.none_prompt[-1]
            ),
        )

        return response.text
        
    
    def fetchRecipe(self, item: str):
        # gets the required recipe from Spoonacular API
        recipe = self.sp_api.search_recipes_complex(
            query = item,
            number = 1 # default for now
        )
        recipe_dict = eval(recipe.text)
        recipe = self.sp_api.get_recipe_information(
            id = recipe_dict['results'][0]['id']
        )
        return recipe.text
    
    def handleNoneIntent(self) -> str:
        # handle the case when the system detects a None intent
        # Process:
        # 1. Get the response from the model, save it as the model's response
        # 2. Return the response as a string
        if self.is_contextual:
            print("Guiding the user through the recipe for the item")
            # if the chat mode is contextual, return the response as is
            response = self.client.models.generate_content(
                model = self.model,
                contents = self.system_memory,
                config = types.GenerateContentConfig(
                    system_instruction = self.none_prompt[-1]
                )
            )
            # if the response is "Done", we quit the contextual response and get a normal response
            if "Done" in response.text:

                # pop the last prompt (usually, the one on guiding the user through the recipe)
                self.none_prompt.pop()

                # switch off the contextual mode
                self.is_contextual = False

                # get a normal response from the model
                response = self.client.models.generate_content(
                    model = self.model,
                    contents = self.system_memory,
                    config = types.GenerateContentConfig(
                        system_instruction = self.none_prompt[-1]
                    )
                )
        else:
            print("Normal chat")
            # go for a usual conversation
            response = self.client.models.generate_content(
                model = self.model,
                contents = self.system_memory,
                config = types.GenerateContentConfig(
                    system_instruction = self.none_prompt[-1]
                )
            )

        self.system_memory.append(
            types.Content(
                role = 'assistant',
                parts = [
                    types.Part.from_text(text = response.text)
                ]
            )
        )

        return response.text

    def run(self):
        # run the system
        # flow:
        # 1. Analyze intent
        # 2. If None intent found, handle like a regular conversation
        # 3. If fetch recipe intent found, call the handleFetchRecipe function, add the recipe to the system chat memory
        # 4. Use the chat memory as the context for the system to keep the conversation going
        while True:
            user_input = input("User:")
            intent = self.getIntent(user_input)
            if 'None' in intent.text:
                print(self.handleNoneIntent())
            else:
                # the output comes as a text repr. of a JSON/Python dictionary
                # we need to convert it first
                output = intent.text
                print(self.handleFetchRecipe(output))


if __name__ == "__main__":
    # create an instance of the agent
    agent = AIAgent()
    # run the agent
    agent.run()