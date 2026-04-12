import os
import firebase_admin
from firebase_admin import credentials, firestore


class _MockDocSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _MockDocument:
    def __init__(self, store, doc_id):
        self.store = store
        self.doc_id = doc_id

    def get(self):
        return _MockDocSnapshot(self.store.get(self.doc_id))

    def set(self, value):
        self.store[self.doc_id] = value


class _MockCollection:
    def __init__(self, db_store, name):
        self.db_store = db_store
        self.name = name
        if name not in self.db_store:
            self.db_store[name] = {}

    def document(self, doc_id):
        return _MockDocument(self.db_store[self.name], doc_id)


class MockFirestoreClient:
    def __init__(self):
        self._store = {}

    def collection(self, name):
        return _MockCollection(self._store, name)


def _init_firestore_client():
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    if os.path.exists(cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    return MockFirestoreClient()


db = _init_firestore_client()
