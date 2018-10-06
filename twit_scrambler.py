
import datetime as dt
import http.client, urllib
import json
import os
import random
import re

import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

import twitter

TEST_MODE = False

PATH = os.path.dirname(os.path.realpath(__file__))
URL_PATT = re.compile(r'http(s)?:\/\/(\w|\.|\/|\?)+')
DATA_FILE_NAMING_CONV = PATH + '/%s_data.txt'
DEFAULT_LOOKBACK = 14
DEFAULT_TWEETS_TO_MIX = 10
MIN_WORDS = 10
MIN_SWAP_WORD_LEN = 4
MIN_SWAPS_TO_MAKE = 2
TWEETS_TO_PULL = 100
TWEET_CHAR_LIMIT = 279
TWT_FIELDS = 'full_text'
POST_TO_TWITTER = not TEST_MODE
WORD = 0
WTYPE = 1
TARGET_TWEET_OVERRIDE = None

# Set the twitter accounts to pull tweets from.
TWITTER_ACCOUNTS = [
    {'handle':'realDonaldTrump', 'lookback':14, 'tweets_to_mix':25, 'mix_perc':0.6},
    {'handle':'SarahPalinUSA', 'lookback':14, 'tweets_to_mix':25, 'mix_perc':0.6},
    {'handle':'newtgingrich', 'lookback':14, 'tweets_to_mix':25, 'mix_perc':0.6},
    {'handle':'seanhannity', 'lookback':14, 'tweets_to_mix':25, 'mix_perc':0.6},
    {'handle':'mike_pence', 'lookback':14, 'tweets_to_mix':25, 'mix_perc':0.6},
]

TYPES_TOSWAP = (
    'VB',   # Verbs
    'VBG',  # Verbs ending in 'ING'
    'NN',   # Nouns
    'NNS',  # Plural Nouns
    'NNP',  # Proper Nouns
    'NNPS', # Proper plural Nouns
    'JJ',   # Adjective
)

SWAP_BLACK_LIST = (
    '@', 'of', 'in', 'at', 't', 'doesn', 'can', '-', ':', '?', '[', ']', '{', '}',
    'be', 'do', ',', '.', '"', '\'', '`', 'great'
)

HTML_SWAPS = {
      '&gt;': '>',
      '&lt;': '<',
      '&apos;': "'",
      '&quot;': '"',
      '&amp;': '&'
}


def send_alert(message):
    print(f'sending alert: {message}')
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
        urllib.parse.urlencode({
            "token": "a3wtbecwv4wkbrab1m58uk3jkpider",
            "user": "u5udyc93zdq44x2yvr68bfykp6b5dj",
            "message": message
        }), { "Content-type": "application/x-www-form-urlencoded" })


def skip_word(word):
    return (
        word.lower() in SWAP_BLACK_LIST
        or bool(re.match(r'^\d+$', word))
        or bool(re.match(r'^\d\d\:\d\d$', word))
    )


def clean_word_array(word_array):
    # NLTK isn't perfect. example: 'United States' gets broken up into 2 separate words but we'd like to
    # treat it like 1x Proper Noun.
    # Implement logic in this function to fix these errors.

    # 2nd to last element is the final string that should appear in the string
    # last element is the word type
    # elements 0 through length-3 are the strings to search for
    forced_pairs = [
        ('united', 'states', 'United States', 'NNP'),
        ('brett', 'kavanaugh', 'Brett Kavanaugh', 'NNP'),
        ('judge', 'kavanaugh', 'Judge Kavanaugh', 'NNP'),
        ('mike', 'pense', 'Mike Pense', 'NNP'),
        ('jeff', 'sessions', 'Jeff Sessions', 'NNP'),
        ('donald', 'trump', 'Donald Trump', 'NNP'),
        ('west', 'virginia', 'West Virginia', 'NNP'),
        ('north', 'carolina', 'North Carolina', 'NNP'),
        ('south', 'carolina', 'South Carolina', 'NNP'),
        ('new', 'york', 'New York', 'NNP'),
        ('new', 'jersey', 'New Jersey', 'NNP'),
        ('new', 'mexico', 'New Mexico', 'NNP'),
        ('nancy', 'pelosi', 'Nancy Pelosi', 'NNP'),
    ]

    words = [w[WORD] for w in word_array]
    cleaned_words = [w[WORD].lower().replace(' ', '') for w in word_array]
    
    for fixes in forced_pairs:
        if all(w in cleaned_words for w in fixes[:-2]):

            # make sure the fix words are next to each other
            # https://stackoverflow.com/questions/33575235/python-how-to-see-if-the-list-contains-consecutive-numbers
            ixs = [cleaned_words.index(w) for w in fixes[:-2]]
            if sorted(ixs) != list(range(min(ixs), max(ixs)+1)):
                print(ixs, 'not consecutive skipping fix!')
                continue

            print("FIXING", fixes)
            ix = cleaned_words.index(fixes[0])
            word_array = [tup for tup in word_array if tup[WORD].lower() not in fixes[:-2]]
            word_array.insert(ix, tuple(fixes[-2:]))
    
    return word_array


def build_mashed_tweet(target_tweet, mix, perc):
    # given a tweet and a mixed bag of words, mash up the tweet
    target_tweet_parts = clean_word_array(nltk.pos_tag(nltk.word_tokenize(target_tweet)))
    print(target_tweet_parts)
    
    # create mashup_map of {word_type: available_worlds[]}
    mix_tweet_parts = []
    for twt in mix:
        mix_tweet_parts += clean_word_array(nltk.pos_tag(nltk.word_tokenize(twt)))
    mashup_map = {}
    mix_tweet_parts = [word for word in mix_tweet_parts if not word[WORD].endswith('..')]

    for word in mix_tweet_parts:
        if word[WORD].lower() in SWAP_BLACK_LIST or len(word[WORD]) < MIN_SWAP_WORD_LEN:
            continue
        
        if word[WTYPE] in mashup_map and mashup_map[word[WTYPE]].count(word[WORD]) == 0:
            mashup_map[word[WTYPE]].append(word[WORD])
        elif word[WTYPE] not in mashup_map:
            mashup_map[word[WTYPE]] = [word[WORD]]
    
    print(mashup_map)
    
    # Create new Tweet
    mashed_tweet = []
    swaps_performed = 0
    for ix, word in enumerate(target_tweet_parts):
        if (ix and word[WTYPE] in TYPES_TOSWAP 
                and len(word[WORD]) >= MIN_SWAP_WORD_LEN
                and word[WTYPE] in mashup_map 
                and not skip_word(word[WORD])
                and random.random() <= perc):
            # Swap out this word
            if len(mashup_map[word[WTYPE]]):
                rand_word = mashup_map[word[WTYPE]].pop(random.randint(0, len(mashup_map[word[WTYPE]])-1))
                mashed_tweet.append(rand_word)
                swaps_performed += 1
                print('SWAPPING "%s" with "%s"' % (word, rand_word))
            else:
                print("skipping swap of", word)
                mashed_tweet.append(word[WORD])
        else:
            print("skipping swap of", word)
            mashed_tweet.append(word[WORD])
    
    mashed_tweet_str = ' '.join(mashed_tweet)
    mashed_tweet_str = mashed_tweet_str.replace(' , ', ', ')\
                                        .replace(' . ', '. ')\
                                        .replace(' ’ ', '’')\
                                        .replace(' \' ', '\'')\
                                        .replace(' !', '!')
    print('swaps_performed', swaps_performed)

    if swaps_performed < MIN_SWAPS_TO_MAKE:
        return None
    
    # remove encoded HTML chars 
    for search, repl in HTML_SWAPS.items():
        if search in mashed_tweet_str:
            mashed_tweet_str = mashed_tweet_str.replace(search, repl)
    
    return twit['handle'] + ': ' + mashed_tweet_str

    
def main(twit, api):

    print('----------', twit['handle'], '-----------')

    # Download Tweets
    resp = api.GetUserTimeline(
        screen_name=twit['handle'],
        count=TWEETS_TO_PULL,
        include_rts=False,
        exclude_replies=True,
        trim_user=True
    )
    resp = [r.AsDict() for r in resp]
    print("got back", len(resp), "tweets")
    print("most recent tweet", repr(resp[0][TWT_FIELDS]))

    # Remove URLs, remove tweets that are too short
    for ix, twt in enumerate(resp):
        resp[ix][TWT_FIELDS] = URL_PATT.sub('', twt[TWT_FIELDS]).strip()
    resp = [r for r in resp if len(r[TWT_FIELDS].split(' ')) >= MIN_WORDS]

    print("most recent CLEANED tweet", repr(resp[0][TWT_FIELDS]))

    # Get tweet IDs we've already used
    try:
        with open(DATA_FILE_NAMING_CONV % twit['handle']) as f:
            used_tweets = f.read().split('\n')
    except IOError:
        used_tweets = []

    
    if not TEST_MODE and resp[0]['id_str'] in used_tweets:
        print("already used this tweet! BYE!")
        return
    else:
        print("\n NEW TWEET FOUND! -_- oh god \n")
    

    # Select a tweet to use (most recent)
    target_tweet = resp.pop(0) if not TEST_MODE else resp.pop(random.randint(0, len(resp)-1))

    # Select older tweets to mix in with new tweet
    mix_tweet = []
    for i in range(twit['tweets_to_mix']):
        if len(resp) > 0:
            max_ix = len(resp)-1
            mix_tweet.append(resp.pop(random.randint(0, max_ix)))
        else:
            break
    if not len(mix_tweet):
        print('mix_tweet is empty')
        return


    print('using this tweet:\n', repr(target_tweet[TWT_FIELDS]))
    print('\n\ntweets to mix in:', '\n'.join(repr(r[TWT_FIELDS]) for r in mix_tweet))

    

    # Generate new tweet 
    new_tweet = build_mashed_tweet(TARGET_TWEET_OVERRIDE or target_tweet[TWT_FIELDS], 
                                    [t[TWT_FIELDS] for t in mix_tweet], twit['mix_perc'])
    print('\n\nnew mashed tweet\n', repr(new_tweet))




    # Post Tweet to Twitter
    def truncate(string):
        if len(string) <= TWEET_CHAR_LIMIT:
            return string
        else:
            return string[0:TWEET_CHAR_LIMIT-2] + '..'
    if POST_TO_TWITTER:

        if new_tweet:
            api.PostUpdate(status=truncate(new_tweet))
            try:
                send_alert(new_tweet)
            except Exception as e:
                print(e)

        # Update txt file with target tweet ID
        used_tweets.insert(0, target_tweet['id_str'])
        used_tweets = used_tweets[0:500]
        with open(DATA_FILE_NAMING_CONV % twit['handle'], 'w') as f:
            for tid in used_tweets:
                if tid:
                    f.write(tid+'\n')
    

if __name__ == '__main__':
    
    with open(PATH+'/creds.json') as f:
        creds = json.load(f)
    
    # Construct API wrapper and authenticate
    creds['tweet_mode'] = 'extended'
    api = twitter.Api(**creds)
    if not api.VerifyCredentials():
        raise Exception("Could not verify twitter api credentials")

    for twit in TWITTER_ACCOUNTS:
        main(twit, api)