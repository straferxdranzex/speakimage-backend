import os
import json
import openai
import logging
import requests
from datetime import timedelta
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin
from flask import Flask, request, jsonify, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from db.operations import DB_OPERATOR
from db.utils import get_curr_timestamp
from prompt import PROMPT_TO_ANALYSE_QUERY

logging.basicConfig(level=logging.DEBUG)  # Set logging level to debug for detailed logs

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(days=15)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = False
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
app.config["PIXABAY_API_KEY"] = os.getenv("PIXABAY_API_KEY")

DBOPR = DB_OPERATOR()
OAI_MODEL = "gpt-3.5-turbo-0125"
DALL_E_MODEL = "dall-e-3"
IMG_SIZE = "1024x1024"

openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai


@app.route("/api/health", methods=["GET"])
@cross_origin()
def health_check():
    logging.debug("Health check endpoint was called.")
    response = make_response(jsonify({"status": "healthy"}))
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 200

@app.route("/")
@cross_origin()
def home():
    return jsonify({"message": "Welcome to the Speak Image Backend!"})

def analyse_query(query):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "Generate an image related to description.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "The description of image which needs to be generated",
                        }
                    },
                    "required": ["description"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_answer",
                "description": "Get the text response for the query from the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query from the user that needs to be answered",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
    ]

    messages = [
        {"role": "system", "content": PROMPT_TO_ANALYSE_QUERY},
        {"role": "user", "content": query},
    ]
    response = client.chat.completions.create(
        model=OAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,
    )
    return response

def call_tool_funcs(tool_calls):
    outputs = {}
    for tool_call in tool_calls:
        if tool_call.type == "function":
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            function_to_call = globals().get(function_name)
            if function_to_call:
                try:
                    output = function_to_call(**args)
                    outputs[function_name] = output
                except TypeError as e:
                    logging.error(f"Argument mismatch in {function_name}: {str(e)}")
                    logging.debug(f"Received arguments for {function_name}: {args}")
                    continue
    return outputs

def get_answer(query):
    messages = [
        {
            "role": "system",
            "content": "Answer with a bit of detailed explanation. There could be causal question or specific question.",
        },
        {"role": "user", "content": query},
    ]
    response = client.chat.completions.create(model=OAI_MODEL, messages=messages)
    response_message = response.choices[0].message
    logging.debug(f"MESSAGE: {response_message}")
    return response_message.content

def get_video_from_pixabay(description):
    url = f"https://pixabay.com/api/videos/?key={app.config['PIXABAY_API_KEY']}&q={description}"
    response = requests.get(url)
    out = response.json()
    if out.get("hits"):
        return out["hits"][0]["videos"]["medium"]["url"]
    return None

def get_image_from_pixabay(description):
    url = f"https://pixabay.com/api/?key={app.config['PIXABAY_API_KEY']}&q={description}&image_type=photo"
    response = requests.get(url)
    out = response.json()
    if out.get("hits"):
        large_img_url = out["hits"][0].get("largeImageURL")
        return large_img_url if large_img_url else out["hits"][0]["imageURL"]
    return None

def generate_image(description):
    response = client.images.generate(
        model=DALL_E_MODEL, prompt=description, size=IMG_SIZE, n=1, quality="standard"
    )
    gpt_image_url = response.data[0].url if response.data else None
    pixabay_img_url = get_image_from_pixabay(description)
    video_url = get_video_from_pixabay(description)
    return gpt_image_url, pixabay_img_url, video_url

def chat(user_query):
    response = analyse_query(user_query)
    if not response.choices or not response.choices[0].message:
        error_msg = "Invalid response structure received from OpenAI."
        logging.error(f"{error_msg} Full response: {response}")
        return {"error": error_msg}
    tool_calls = response.choices[0].message.tool_calls
    outputs = (
        call_tool_funcs(tool_calls)
        if tool_calls
        else {"get_answer": get_answer(user_query)}
    )
    text = outputs.get("get_answer")
    gpt_image_url, pixabay_img_url, video_url = outputs.get(
        "generate_image", (None, None, None)
    )
    res_out = {
        "text": text,
        "dalle_image": gpt_image_url,
        "pixabay_img": pixabay_img_url,
        "pixabay_video": video_url,
    }
    return {"response": res_out}

@app.route("/api/init-chat", methods=["POST"])
@cross_origin()
def init_chat():
    user_query = request.json.get("query")
    title_words = user_query.split(" ")[:5]
    title = " ".join(title_words)
    user_id = request.json.get("user_id")
    if not user_query or not user_id:
        return jsonify({"error": "user_query or user_id missing"}), 400
    logging.debug(f"user query: {user_query}")
    res_out = chat(user_query)
    if "response" in res_out:
        conversation = {
            "query": user_query,
            "response": res_out["response"],
            "timestamp": get_curr_timestamp(),
        }
        thread_id = DBOPR.init_chat_in_db(user_id, title, conversation)
        logging.debug(f"Thread ID: {thread_id}")
        return jsonify({"response": res_out["response"], "thread_id": thread_id}), 200
    return jsonify(res_out), 500

@app.route("/api/generate-answer", methods=["POST"])
@cross_origin()
def generate_answer():
    user_query = request.json.get("query")
    thread_id = request.json.get("thread_id")
    logging.info(f"Received Query: {user_query} | Thread ID: {thread_id}")
    if not user_query or not thread_id:
        logging.error("No query or thread_id provided in request")
        return jsonify({"error": "No query or thread_id provided"}), 400
    try:
        res_out = chat(user_query)
        if "response" in res_out:
            conversation = {
                "query": user_query,
                "response": res_out["response"],
                "timestamp": get_curr_timestamp(),
            }
            DBOPR.add_message(thread_id, conversation)
            return jsonify(res_out), 200
        return jsonify(res_out), 500
    except Exception as e:
        logging.error(f"API request failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/history", methods=["POST"])
@cross_origin()
def chat_history():
    thread_id = request.json.get("thread_id")
    conversation = DBOPR.get_history(thread_id)
    if conversation:
        return jsonify(conversation), 200
    return jsonify({"error": "Chat history not found"}), 404

@app.route("/api/clear-history", methods=["POST"])
@cross_origin()
def clear_history():
    thread_id = request.json.get("thread_id")
    success = DBOPR.clear_history(thread_id)
    if success:
        return jsonify({"message": "Chat history cleared"}), 200
    return jsonify({"error": "Chat history not found"}), 404

@app.route("/api/delete-chat", methods=["POST"])
@cross_origin()
def delete_chat():
    thread_id = request.json.get("thread_id")
    DBOPR.delete_chat(thread_id)
    return jsonify({"message": "chat deleted"}), 200

@app.route("/signup", methods=["POST"])
@cross_origin()
def signup():
    data = request.get_json()
    logging.debug('Data received: %s', data)
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")
    if email and password and full_name:
        existing_user = DBOPR.find_user(email)
        if existing_user:
            return jsonify({"error": "User already exists"}), 409
        hashed_password = generate_password_hash(password)
        DBOPR.create_user(email, hashed_password, full_name)
        return jsonify({"message": "User created successfully"}), 201
    return jsonify({"error": "Invalid data"}), 400

@app.route("/login", methods=["POST"])
@cross_origin()
def login():
    data = request.get_json()
    logging.debug(f"Received login data: {data}")

    email = data.get("email")
    password = data.get("password")

    if email and password:
        logging.debug(f"Attempting to find user with email: {email}")
        user = DBOPR.find_user(email)

        if user:
            logging.debug(f"User found: {user}")
            if check_password_hash(user["password"], password):
                logging.debug("Password check passed")
                session.permanent = True
                session["email"] = email
                user_id = user["_id"]  # Get the user_id
                logging.debug(f"Login successful for user_id: {user_id}")
                response = jsonify({"message": "Login successful", "user_id": user_id})
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin")
                return response, 200
            else:
                logging.warning("Invalid password provided")
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            logging.warning("User not found")
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        logging.error("Invalid data received in request")
        return jsonify({"error": "Invalid data"}), 400

@app.route("/logout", methods=["POST"])
@cross_origin()
def logout():
    session.pop("username", None)
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/api/get-users", methods=["GET"])
@cross_origin()
def get_users():
    try:
        users = DBOPR.get_users()
        if users is not None:
            return jsonify(users), 200
        else:
            return jsonify({"error": "Error fetching users"}), 500
    except Exception as e:
        logging.error(f"Exception in /api/get-users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/get-chats/<user_id>", methods=["GET"])
@cross_origin()
def get_chats(user_id):
    try:
        chats = DBOPR.get_chats_by_user_id(user_id)
        if chats is not None:
            return jsonify(chats), 200
        else:
            return jsonify({"error": "Error fetching chats"}), 500
    except Exception as e:
        logging.error(f"Exception in /api/get-chats: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/get-chat/<chat_id>", methods=["GET"])
@cross_origin()
def get_chat_by_id(chat_id):
    logging.debug(f"Fetching chat with ID: {chat_id}")
    chat = DBOPR.get_chat_by_id(chat_id)
    if chat:
        return jsonify(chat), 200
    else:
        return jsonify({"error": "Chat not found"}), 404

@app.route("/api/get-user-chats/<user_id>", methods=["GET"])
@cross_origin()
def get_user_chats(user_id):
    logging.debug(f"Fetching chats for user_id: {user_id}")
    chats = DBOPR.get_chats_by_user_id(user_id)
    if chats:
        return jsonify(chats), 200
    else:
        return jsonify({"error": "Chats not found"}), 404

@app.route("/api/get-user/<user_id>", methods=["GET"])
@cross_origin()
def get_user(user_id):
    try:
        user = DBOPR.get_user_by_id(user_id)
        if user is not None:
            logging.debug(f"User found: {user}")
            return jsonify(user), 200
        else:
            logging.warning(f"User not found with ID: {user_id}")
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        logging.error(f"Exception in /api/get-user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
