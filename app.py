from flask import Flask
from flask import request
from flask import render_template
from flask import url_for
from flask import redirect

import json
import bson

import pandas as pd

from pymongo import MongoClient


# instantiate the flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret!'

# Initialize Mongo
client = MongoClient()
db = client.test_db

def get_next_tweet():
    return db.tweets.find_one_and_update(
        {'fetched' : False, 'processed' : False},
        {'$set' : {'fetched' : True}}
    )

@app.route('/')
def index():
    return render_template('index.html', tweet=get_next_tweet())


# when a user exits the web page or clicks a link, we want to reset
# the fetched value in db
@app.route('/status', methods=['POST'])
def vote_tweet_status():
    json_data = request.get_json()
    tweet_id = json_data['tweet_id']

    results = db.tweets.find_one(
        {"_id": bson.ObjectId(oid=str(tweet_id))}
    )

    if results['processed'] == False:
        if results['fetched'] == True:
            db.tweets.update(
                {"_id": bson.ObjectId(oid=str(tweet_id))},
                {"$set":
                    {
                        "fetched": False,
                    }
                }
            )
            return "fetched value reset"

    return "was processed successfully"




@app.route('/vote', methods=['POST'])
def vote_tweet():
    json_data = request.get_json()
    tweet_id = json_data['tweet_id']
    sentiment = json_data['sentiment']

    db.tweets.update(
        {"_id": bson.ObjectId(oid=str(tweet_id))},
        { "$set":
            {
                "processed" : True,
                "sentiment" : sentiment
            }
        }
    )
    return redirect(url_for("index"))


if __name__ == '__main__':

    # drops our current DB
    # mainly was for testing
    client.drop_database('test_db')

    # before launching our web app, we want to store our file in mongo
    #tweets = pd.read_csv('bitcoin-tweets.csv')

    tweets = pd.read_json('bitcoin-03.json', lines=True)

    # we only want tweets that are in english
    # and are original tweets! We don't care about re-tweets
    tweets = tweets[ (tweets['lang'] == 'en') & (pd.isnull(tweets['retweeted_status'])) ]

    # only take out what we need
    tweets_cleaned = tweets[['created_at', 'text', 'id']]

    # for the web-app when people vote on the sentiment
    tweets_cleaned['fetched'] = False
    tweets_cleaned['processed'] = False

    # store to our db
    data_json = json.loads(tweets_cleaned.to_json(orient='records'))
    db.tweets.insert(data_json)

    # start our app
    app.run()

