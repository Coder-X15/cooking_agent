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
        print "Fetch the recipe for <name of the dish with every letter in lower-case and seperated by underscores>", otherwise print "None" '''

        self.none_prompt = '''Converse with the user almost like how a normal human user would. Be suggestive when it comes to ideas,
        ask opinions subtly (like "Ain't that so?", "What do you think", etc.). Hide as much of your bot behaviour as you can.'''

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
        # changes the chat mode into a guide for the user while cooking
        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(tools=[self.fetch_recipe_tool]),
        )

        function_call_part = response.function_calls[0]
        function_call_content = response.candidates[0].content
        recipe = None
        contextual_chat = []

        try:
            # parse the function call to get the item name
            item_name = function_call_part.args['item']

            # get the recipe for the item
            recipe = self.fetchRecipe(item_name)
            function_response = {'result': recipe}
        except:
            # raise an exception
            raise Exception("Failed to get the recipe for the item")
        
        working_prompt = '''Guide the user, step-by-step, through the recipe for the item. Do list the quantity when you list ingredients. Wait when the user gives signs for you to pause.
        Once the whole recipe has been done or the user doesn't seems to have decided not to cook anything, return "Done".'''

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

        contextual_chat += [
                user_prompt_content,
                function_call_content,
                function_response_content,
            ]
        
        while response != "Done":

            # generate the response
            response = self.client.models.generate_content(
                model=self.model,
                contents=contextual_chat,
                config=types.GenerateContentConfig(
                    tools=[self.fetch_recipe_tool],
                    system_instruction= working_prompt,
                    temperature=0.7,
                ),
            )

            # yield it if the reply is not "Done"
            print(f"Assistant:{response.text if "Done" not in response.text else "Fine..."}")

            # add it to the contextual chat
            contextual_chat.append(
                types.Content(
                    role = 'assistant',
                    parts = [types.Part.from_text(text = response.text)]
                )
            )

            # reset variable
            response = response
            

            if response != "Done":
                # get user input
                query = input("User:")

                # create user prompt content and push it to the contextual chat
                user_prompt_content = types.Content(
                    role = 'user',
                    parts = [
                        types.Part.from_text(text = query)
                    ]
                )

                contextual_chat.append(
                    user_prompt_content
                )

        return contextual_chat

        
    
    def fetchRecipe(self, item: str):
        # gets the required recipe from Spoonacular API
        recipe = self.sp_api.search_recipes_complex(
            query = item,
            number = 1 # default for now
        )

        return recipe.text
    
    def handleNoneIntent(self) -> str:
        # handle the case when the system detects a None intent
        # Process:
        # 1. Get the response from the model, save it as the model's response
        # 2. Return the response as a string
        response = self.client.models.generate_content(
            model = self.model,
            contents = self.system_memory[-1].parts[0],
        )
        self.system_memory.append(
            types.Content(
                role = 'assistant',
                parts = [
                    types.Part.from_text(text = response.text)
                ]
            )
        )

        return response.candidates[0].content.parts[0].text.strip()

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
                self.system_memory += self.handleFetchRecipe(output)

if __name__ == "__main__":
    assistant = AIAgent()
    assistant.run()