
from flask import Flask, jsonify, request

app = Flask(__name__)

photos = [
    {
        "id": 1,
        "caption": "Sunset over Durham",
        "latitude": 54.7732,
        "longitude": -1.5760
    }
]

@app.route("/api/photos", methods=["GET"])
def get_photos():
    return jsonify(photos)

@app.route("/api/photos", methods=["POST"])
def create_photo():
    data = request.get_json()

    photo = {
        "id": len(photos) + 1,
        "caption": data["caption"],
        "latitude": data["latitude"],
        "longitude": data["longitude"]
    }

    photos.append(photo)

    return jsonify(photo), 201

if __name__ == "__main__":
    app.run(debug=True)
