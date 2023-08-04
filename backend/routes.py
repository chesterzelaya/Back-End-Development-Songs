from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for, Response  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='OK'), 200

@app.route('/count', methods=['GET'])
def count():
    return jsonify(count=db.songs.count_documents({})), 200

@app.route('/song', methods=['GET'])
def get_songs():
    """ Retrieve all songs """
    results = []
    for doc in db.songs.find():
        results.append(parse_json(doc)) 
    return jsonify(songs=results), 200

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    """ Retrieve a single song """
    doc = db.songs.find_one({"id": id})
    if doc:
        return jsonify(parse_json(doc)), 200  
    else:
        abort(404, f"Song with id {id} not found") 
    
@app.route('/song', methods=['POST'])
def create_song():
    """ Create a new song """
    if not request.json or 'id' not in request.json:
        abort(400, "The 'id' field is required.")

    id = request.json['id']
    doc = db.songs.find_one({"id": id})

    if doc:
        return jsonify({"Message": f"Song with id {id} already present"}), 302 
    else:
        result = db.songs.insert_one(request.json)

        if isinstance(result.inserted_id, ObjectId):
            return jsonify({"inserted id": str(result.inserted_id)}), 201  
        else:
            return jsonify({"inserted id": id}), 201


@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    """ Update an existing song"""
    doc = db.songs.find_one({"id": id})
    if doc:
        doc_without_id = {k: v for k, v in doc.items() if k != '_id'}
        if doc_without_id == request.json:
            return {"message": "song found, but nothing updated"}, 200
        db.songs.update_one({"id": id}, {"$set": request.json})
        updated_doc = db.songs.find_one({"id": id})  
        return json.dumps(parse_json(updated_doc)), 201
    else:
        return {"message": "song not found"}, 404

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    """ Delete a song """
    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    else:
        return Response(status=204)
