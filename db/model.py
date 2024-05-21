import os
import certifi
import pymongo
from dotenv import load_dotenv


class MODEL:
    def __init__(self, database_name, collection_name):
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        try:
            load_dotenv()
            self.MONGO_URL_STATIC = os.environ["MONGO_URL_STATIC"]
        except:
            raise Exception("Set MONGO_URL_STATIC in env variable...")

    def __enter__(self):
        self.client = pymongo.MongoClient(
            self.MONGO_URL_STATIC, tlsCAFile=certifi.where()
        )
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def find_document(self, query):
        return self.collection.find_one(query)

    def find_all_documents(self, query):
        cursor = self.collection.find(query)
        return [doc for doc in cursor]

    def document_exist(self, query):
        return self.collection.count_documents(query, limit=1)

    def insert_document(self, doc):
        res = self.collection.insert_one(doc)
        return res.inserted_id

    def update_one(self, filter_criteria, update_operation):
        result = self.collection.update_one(filter_criteria, update_operation)
        print(
            f"Matched {result.matched_count} document(s) and modified {result.modified_count} document(s)."
        )
        return result

    def update_many(self, filter_criteria, update_operation):
        result = self.collection.update_many(filter_criteria, update_operation)
        print(
            f"Matched {result.matched_count} document(s) and modified {result.modified_count} document(s)."
        )
        return result

    def delete_first(self, query):
        result = self.collection.find_one_and_delete(query)
        if result:
            print("Deleted document")
        else:
            print("No matching document found to delete")
        return result

    def delete_as_many(self, query):
        result = self.collection.delete_many(query)
        print("Deleted", result.deleted_count, "documents")
        return result

    def get_all(self):
        return [x for x in self.collection.find()]

    def remove_all(self):
        result = self.collection.delete_many({})
        print(result.deleted_count, " documents deleted!!")
        return result
