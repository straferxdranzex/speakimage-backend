PROMPT_TO_ANALYSE_QUERY = """
    Analyse the user query, if it is better to answer with an image and text than use the generate_image and get_answer functions. 
    Depending on the query you can use both functions or only get_answer. You must use the get_answer func to respond to query. 
        Here are sample question for which you should use both functions:
        In these type of question like what is stop sign? 
        what is heart?
        how does the human skeleton look?
        what is a beautiful natural scene?
"""