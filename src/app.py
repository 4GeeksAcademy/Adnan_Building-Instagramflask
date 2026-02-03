"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS

from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User 

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)


# -------------------------
# Error handling
# -------------------------
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


# -------------------------
# Sitemap + Swagger
# -------------------------
@app.route("/")
def sitemap():
    return generate_sitemap(app)


@app.route("/swagger")
def swagger_docs():
    return jsonify(swagger(app))


# -------------------------
# Helpers
# -------------------------
def get_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def require_fields(data, fields):
    missing = [f for f in fields if data.get(f) in (None, "", [])]
    if missing:
        raise APIException(f"Missing required fields: {', '.join(missing)}", status_code=400)


# -------------------------
# Users endpoints
# -------------------------
@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([u.serialize() for u in users]), 200


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        raise APIException("User not found", status_code=404)
    return jsonify(user.serialize()), 200


@app.route("/users", methods=["POST"])
def create_user():
    data = get_json()
    # Your model has nullable=False on is_active, so require it unless you add a default in models.py
    require_fields(data, ["email", "password", "is_active"])

    user = User(
        email=data["email"],
        password=data["password"],
        is_active=bool(data["is_active"])
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(user.serialize()), 201


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        raise APIException("User not found", status_code=404)

    data = get_json()

    # Only update fields that are provided
    if "email" in data:
        if data["email"] in (None, ""):
            raise APIException("email cannot be empty", status_code=400)
        user.email = data["email"]

    if "password" in data:
        if data["password"] in (None, ""):
            raise APIException("password cannot be empty", status_code=400)
        user.password = data["password"]

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify(user.serialize()), 200


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        raise APIException("User not found", status_code=404)

    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "User deleted"}), 200


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=PORT, debug=False)
