PROMPT_TO_ANALYSE_QUERY = """
    Analyze the user query to determine the best response format. Follow these guidelines:

    1. Always use the get_answer function to provide a textual response to the query.
    2. In most cases, enhance the response by also using the generate_image function unless the query is very generic or purely conversational.

    Use the generate_image function for queries like:
        - "How is life on Mars?"
        - "Do Siamese cats sleep a lot?"
        - "What does the Eiffel Tower look like at night?"
        - "Describe a bustling city street."
        - "What is the distance of Mars from Earth?"
        - "How far is the closest star to our solar system?"

    Generally, avoid using the generate_image function for non-specific or conversational queries such as but not limited to:
        - "Hi"
        - "How are you?"
        - "What’s the weather like?"

    This approach ensures that the majority of responses are enriched with visual content unless the query specifically warrants a simple textual response.
"""
