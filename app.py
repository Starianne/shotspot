import os
import uuid
from functools import wraps
from typing import Any, Callable

from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, request
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import RequestEntityTooLarge
from supabase import Client, create_client

load_dotenv()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def create_app(supabase_client: Client | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES)
    )
    app.config["SUPABASE_BUCKET"] = os.getenv("SUPABASE_STORAGE_BUCKET", "photos")
    app.supabase = supabase_client or _create_supabase_client()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_request(_: RequestEntityTooLarge):
        return _error("Image exceeds the configured maximum size.", 413)

    @app.errorhandler(404)
    def handle_not_found(_: Any):
        return _error("Resource not found.", 404)

    @app.route("/api/posts", methods=["GET"])
    def list_posts():
        page, per_page = _pagination()
        if page is None:
            return _error("page must be a positive integer and per_page must be between 1 and 100.", 400)
        start = (page - 1) * per_page
        try:
            result = (
                app.supabase.table("posts")
                .select("*, profiles(username, display_name, avatar_url)")
                .order("created_at", desc=True)
                .range(start, start + per_page - 1)
                .execute()
            )
            return jsonify({"posts": result.data, "page": page, "per_page": per_page})
        except Exception as exc:
            app.logger.exception("Failed to list posts: %s", exc)
            return _error("Unable to retrieve posts.", 500)

    @app.route("/api/posts/<post_id>", methods=["GET"])
    def get_post(post_id: str):
        if not _valid_uuid(post_id):
            return _error("Invalid post ID.", 400)
        try:
            result = (
                app.supabase.table("posts")
                .select("*, profiles(username, display_name, avatar_url)")
                .eq("id", post_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                return _error("Post not found.", 404)
            return jsonify(result.data)
        except Exception as exc:
            app.logger.exception("Failed to retrieve post: %s", exc)
            return _error("Unable to retrieve post.", 500)

    @app.route("/api/posts", methods=["POST"])
    @requires_auth
    def create_post(user: dict[str, Any]):
        image = request.files.get("image")
        if not image or not image.filename:
            return _error("An image file is required.", 400)
        if image.mimetype not in ALLOWED_IMAGE_TYPES:
            return _error("Only JPEG, PNG, and WebP images are supported.", 400)

        metadata = request.form
        caption = metadata.get("caption", "").strip()
        place_name = metadata.get("place_name", "").strip()
        latitude = _number(metadata.get("latitude"))
        longitude = _number(metadata.get("longitude"))
        if not place_name or latitude is None or longitude is None:
            return _error("place_name, latitude, and longitude are required.", 400)
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return _error("Latitude or longitude is outside its valid range.", 400)
        instagram_url = metadata.get("instagram_url", "").strip() or None
        if instagram_url and not (
            instagram_url.startswith("https://www.instagram.com/")
            or instagram_url.startswith("https://instagram.com/")
        ):
            return _error("instagram_url must be a valid HTTPS Instagram URL.", 400)

        image_bytes = image.stream.read(app.config["MAX_CONTENT_LENGTH"] + 1)
        if len(image_bytes) > app.config["MAX_CONTENT_LENGTH"]:
            return _error("Image exceeds the configured maximum size.", 413)

        image_path = f"{user['id']}/{uuid.uuid4()}{ALLOWED_IMAGE_TYPES[image.mimetype]}"
        bucket = app.supabase.storage.from_(app.config["SUPABASE_BUCKET"])
        try:
            bucket.upload(
                image_path,
                image_bytes,
                {"content-type": image.mimetype, "upsert": "false"},
            )
        except Exception as exc:
            app.logger.exception("Failed to upload image: %s", exc)
            return _error("Unable to upload image.", 502)

        payload = {
            "user_id": user["id"],
            "image_url": image_path,
            "caption": caption or None,
            "place_name": place_name,
            "latitude": latitude,
            "longitude": longitude,
            "instagram_url": instagram_url,
        }
        try:
            result = app.supabase.table("posts").insert(payload).execute()
            if not result.data:
                raise RuntimeError("Supabase returned no created post.")
            return jsonify(result.data[0]), 201
        except Exception as exc:
            app.logger.exception("Failed to create post record: %s", exc)
            try:
                bucket.remove([image_path])
            except Exception as cleanup_exc:
                app.logger.exception("Failed to clean up uploaded image: %s", cleanup_exc)
            return _error("Unable to create post.", 500)

    @app.route("/api/posts/<post_id>", methods=["DELETE"])
    @requires_auth
    def delete_post(user: dict[str, Any], post_id: str):
        if not _valid_uuid(post_id):
            return _error("Invalid post ID.", 400)
        try:
            found = (
                app.supabase.table("posts")
                .select("id, user_id, image_url")
                .eq("id", post_id)
                .maybe_single()
                .execute()
            )
            post = found.data
            if not post:
                return _error("Post not found.", 404)
            if post["user_id"] != user["id"]:
                return _error("You do not own this post.", 403)
            bucket = app.supabase.storage.from_(app.config["SUPABASE_BUCKET"])
            bucket.remove([post["image_url"]])
            app.supabase.table("posts").delete().eq("id", post_id).execute()
            return "", 204
        except Exception as exc:
            app.logger.exception("Failed to delete post: %s", exc)
            return _error("Unable to delete post.", 500)

    @app.route("/api/users/<user_id>", methods=["GET"])
    def get_user_profile(user_id: str):
        if not _valid_uuid(user_id):
            return _error("Invalid user ID.", 400)
        try:
            result = (
                app.supabase.table("profiles")
                .select("id, username, display_name, avatar_url, bio, created_at")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            if not result.data:
                return _error("User not found.", 404)
            return jsonify(result.data)
        except Exception as exc:
            app.logger.exception("Failed to retrieve user profile: %s", exc)
            return _error("Unable to retrieve user profile.", 500)

    @app.route("/api/users/<user_id>/posts", methods=["GET"])
    def list_user_posts(user_id: str):
        if not _valid_uuid(user_id):
            return _error("Invalid user ID.", 400)
        page, per_page = _pagination()
        if page is None:
            return _error("page must be a positive integer and per_page must be between 1 and 100.", 400)
        try:
            result = (
                app.supabase.table("posts")
                .select("*, profiles(username, display_name, avatar_url)")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range((page - 1) * per_page, page * per_page - 1)
                .execute()
            )
            return jsonify({"posts": result.data, "page": page, "per_page": per_page})
        except Exception as exc:
            app.logger.exception("Failed to list user posts: %s", exc)
            return _error("Unable to retrieve user posts.", 500)

    return app


def _create_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured.")
    return create_client(url, service_key)


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _number(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _pagination() -> tuple[int | None, int]:
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return None, 20
    if page < 1 or not 1 <= per_page <= 100:
        return None, per_page
    return page, per_page


def requires_auth(route: Callable):
    @wraps(route)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _error("Authentication is required.", 401)
        token = header[7:].strip()
        if not token:
            return _error("Authentication is required.", 401)
        try:
            response = current_app.supabase.auth.get_user(token)
            user = response.user
            if not user:
                return _error("Invalid authentication token.", 401)
            return route(user.model_dump() if hasattr(user, "model_dump") else user, *args, **kwargs)
        except Exception:
            return _error("Invalid authentication token.", 401)

    return wrapped


if __name__ == "__main__":
    create_app().run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
