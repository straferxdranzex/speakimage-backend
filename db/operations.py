import uuid
import logging
from bson.objectid import ObjectId
from db.model import MODEL
from db.utils import get_curr_timestamp


class DB_OPERATOR:
    def __init__(self) -> None:
        self.chat_db = MODEL("visual-gpt-dev", "chats")
        self.user_db = MODEL("visual-gpt-dev", "users")

    def init_chat_in_db(self, user_id, title, conversation):
        with self.chat_db:
            thread_id = self.chat_db.insert_document(
                {
                    "user_id": user_id,
                    "title": title,
                    "conversation": [conversation],
                    "create_timestamp": get_curr_timestamp(),
                }
            )
        return str(thread_id)

    def add_message(self, thread_id, conversation):
        filter_query = {"_id": ObjectId(thread_id)}  # Specify the document's _id
        update_query = {"$push": {"conversation": conversation}}
        with self.chat_db:
            self.chat_db.update_one(filter_query, update_query)

    def get_history(self, thread_id):
        with self.chat_db:
            query = {"_id": ObjectId(thread_id)}  # Specify the document's _id
            doc = self.chat_db.find_document(query)
        if doc:
            doc.pop("_id")
        return doc

    def clear_history(self, thread_id):
        filter_query = {"_id": ObjectId(thread_id)}  # Specify the document's _id
        update_query = {"$set": {"conversation": []}}
        with self.chat_db:
            result = self.chat_db.update_one(filter_query, update_query)
        return result.modified_count > 0

    def delete_chat(self, thread_id):
        filter_query = {"_id": ObjectId(thread_id)}
        with self.chat_db:
            self.chat_db.delete_first(filter_query)

    def create_user(self, email, hashed_password, full_name):
        with self.user_db:
            user_id = self.user_db.insert_document(
                {
                    "_id": uuid.uuid4().hex,
                    "email": email,
                    "password": hashed_password,
                    "full_name": full_name,
                }
            )
        return str(user_id)

    def find_user(self, email):
        with self.user_db:
            user = self.user_db.find_document({"email": email})
        return user

    def user_exist(self, email):
        with self.user_db:
            if self.user_db.find_document({"email": email}):
                return True
        return False

    def get_users(self):
        try:
            with self.user_db:
                users = self.user_db.get_all()
                # Convert ObjectId to string
                for user in users:
                    user["_id"] = str(user["_id"])
            return users
        except Exception as e:
            logging.error(f"Error fetching users: {str(e)}")
            return None

    def get_chats(self):
        try:
            with self.chat_db:
                chats = self.chat_db.get_all()
                # Convert ObjectId to string
                for chat in chats:
                    chat["_id"] = str(chat["_id"])
            return chats
        except Exception as e:
            logging.error(f"Error fetching chats: {str(e)}")
            return None

    def get_chat_by_id(self, chat_id):
        try:
            with self.chat_db:
                chat = self.chat_db.find_document({"_id": ObjectId(chat_id)})
                if chat:
                    chat["_id"] = str(chat["_id"])
            return chat
        except Exception as e:
            logging.error(f"Error fetching chat by ID: {str(e)}")
            return None

    def get_user_chats_ids(self, user_id):
        try:
            with self.chat_db:
                chats = self.chat_db.find_all_documents({"user_id": user_id})
                chats = [str(c["_id"]) for c in chats]
                print(chats)
            return chats
        except Exception as e:
            logging.error(f"Error fetching chats for user_id: {str(e)}")
            return None

    def get_chats_by_user_id(self, user_id):
        try:
            with self.chat_db:
                chats = self.chat_db.find_all_documents({"user_id": user_id})
                for chat in chats:
                    chat["_id"] = str(chat["_id"])
            return chats
        except Exception as e:
            logging.error(f"Error fetching chats for user_id: {str(e)}")
            return None
