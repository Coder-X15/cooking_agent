from flask import Flask, render_template, request, redirect, url_for
from agent.global_agent import *


# first we need to create a child class out of the AIAgent class to enable proper functionality
class Agent(AIAgent):

    def __init__(self):
        super().__init__()
        self.contextual_chat = [] # keeps the chat context

    # we'll have to first override the handleFetchRecipe function with an implementation that keeps the context
    # even after the redirect.

    def handleFetchRecipe(self, query):
        # changes the chat mode into a guide for the user while cooking
        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(tools=[self.fetch_recipe_tool]),
        )

        function_call_part = response.function_calls[0]
        function_call_content = response.candidates[0].content
        recipe = None

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

        self.contextual_chat += [
                user_prompt_content,
                function_call_content,
                function_response_content,
            ]
        
        if response != "Done":

            # generate the response
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.contextual_chat,
                config=types.GenerateContentConfig(
                    tools=[self.fetch_recipe_tool],
                    system_instruction= working_prompt,
                    temperature=0.7,
                ),
            )

            # add it to the contextual chat
            self.contextual_chat.append(
                types.Content(
                    role = 'assistant',
                    parts = [types.Part.from_text(text = response.text)]
                )
            )

        return response.candidates[0].content
    