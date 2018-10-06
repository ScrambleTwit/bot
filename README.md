# twit-scrambler

### A Twitter bot that randomly scrambles a user's tweet.

## How it works

1) A user's most recent tweet is selected and parsed with natural language tool kit.
2) A random selection of recent tweets are selected and parsed with natural language tool kit.
3) A random selection of verbs, verbs ending in "ing", nouns, plural nouns, and proper nouns from the target tweet are swapped out with corresponding word types from the pool of words from the recent tweets.
4) The mashed up tweet is posted.

## Setup
Create creds.json
```bash
$ cd twit-scrambler
$ echo '{
    "consumer_key": "YOUR_TWITTER_CONSUMER_KEY",
    "consumer_secret": "YOUR_TWITTER_CONSUMER_SECRET_KEY",
    "access_token_key": "YOUR_TWITTER_ACCESS_TOKEN_KEY",
    "access_token_secret": "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
}' > creds.json
```

```python

# Target specific twitter accounts
TWITTER_ACCOUNTS = [
    {'handle':'myTwitterHandle', 'lookback':14, 'tweets_to_mix':5, 'mix_perc':0.65}
]
```

## Run script
```bash
$ python twit_scrambler.py
```

