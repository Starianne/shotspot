import io
import uuid

from app import create_app


USER_ID = str(uuid.uuid4())
POST_ID = str(uuid.uuid4())


class Result:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, client, table):
        self.client, self.table_name = client, table
        self.operation = "select"

    def select(self, *_args):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args):
        return self

    def eq(self, field, value):
        self.client.last_filter = (self.table_name, field, value)
        return self

    def maybe_single(self):
        return self

    def insert(self, payload):
        self.client.inserted = payload
        self.operation = "insert"
        return self

    def delete(self):
        self.client.deleted = True
        self.operation = "delete"
        return self

    def execute(self):
        if self.operation == "insert":
            return Result([{"id": POST_ID, **self.client.inserted}])
        if self.table_name == "posts" and self.client.last_filter and self.client.last_filter[1] == "id":
            return Result(self.client.post[0])
        return Result([])


class Auth:
    def get_user(self, token):
        if token not in {"valid", "other"}:
            raise ValueError("invalid token")
        user_id = USER_ID if token == "valid" else str(uuid.uuid4())
        return type("Response", (), {"user": {"id": user_id}})()


class StorageBucket:
    def __init__(self, client):
        self.client = client

    def upload(self, path, content, options):
        self.client.uploaded = (path, content, options)

    def remove(self, paths):
        self.client.removed = paths


class Storage:
    def __init__(self, client):
        self.client = client

    def from_(self, _bucket):
        return StorageBucket(self.client)


class SupabaseStub:
    def __init__(self):
        self.auth = Auth()
        self.storage = Storage(self)
        self.post = [{"id": POST_ID, "user_id": USER_ID, "image_url": "file.jpg"}]
        self.inserted = None
        self.deleted = False
        self.last_filter = None

    def table(self, name):
        return Query(self, name)


def make_client():
    return create_app(SupabaseStub()).test_client()


def test_create_post_requires_authentication():
    response = make_client().post("/api/posts")
    assert response.status_code == 401


def test_create_and_delete_post():
    client = make_client()
    response = client.post(
        "/api/posts",
        headers={"Authorization": "Bearer valid"},
        data={
            "image": (io.BytesIO(b"image bytes"), "photo.jpg"),
            "place_name": "Durham",
            "latitude": "54.7732",
            "longitude": "-1.576",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert response.get_json()["user_id"] == USER_ID

    response = client.delete(
        f"/api/posts/{POST_ID}", headers={"Authorization": "Bearer valid"}
    )
    assert response.status_code == 204


def test_get_post_and_reject_delete_by_other_user():
    client = make_client()
    response = client.get(f"/api/posts/{POST_ID}")
    assert response.status_code == 200
    assert response.get_json()["id"] == POST_ID

    response = client.delete(
        f"/api/posts/{POST_ID}", headers={"Authorization": "Bearer other"}
    )
    assert response.status_code == 403


def test_create_post_rejects_invalid_coordinates():
    response = make_client().post(
        "/api/posts",
        headers={"Authorization": "Bearer valid"},
        data={
            "image": (io.BytesIO(b"image bytes"), "photo.jpg"),
            "place_name": "Durham",
            "latitude": "91",
            "longitude": "0",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
