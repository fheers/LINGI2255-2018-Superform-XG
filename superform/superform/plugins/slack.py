from datetime import datetime,timedelta

from flask import Blueprint, redirect, url_for, request
from slackclient import SlackClient
import json
from superform.models import Channel, Publishing, db
from superform.utils import get_module_full_name
from superform.suputils import keepass

FIELDS_UNAVAILABLE = []
CONFIG_FIELDS = ["channel_name","slack_channel_name", "slack_access_token", "slack_token_expiration_date"]

API_CLIENT_KEY = keepass.get_password_from_keepass('slack_client_key')
API_SECRET = keepass.get_password_from_keepass('slack_secret')
API_CLIENT_ID = keepass.get_password_from_keepass('slack_client_id')

slack_verify_callback_page = Blueprint('slack', 'channels')


slackClient =  SlackClient();
def authenticate(channel_name, publishing_id):

    previous_token = SlackTokens.get_token(SlackTokens, channel_name)

    if previous_token.__getitem__(0) is None or (datetime.now() > previous_token.__getitem__(1)) :

        conf = dict()
        conf["channel_name"] = channel_name
        conf["publishing_id"] = publishing_id

        state = json.dumps(conf)
        return "https://slack.com/oauth/authorize?scope=identity.basic&client_id="+API_CLIENT_ID+"&state="+state  # open this url on your browser
    else:
        return 'AlreadyAuthenticated'


def set_access_token(channel_name, code):
    # An empty string is a valid token for this request
    sc = SlackClient("")

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        "oauth.access",
        client_id=API_CLIENT_ID,
        client_secret=API_SECRET,
        code=code
    )

    print(auth_response)
    # Add
    # channel = Channel.query.filter_by(name=channel_name, module=get_module_full_name("linkedin")).first()
    # add the configuration to the channel
    conf = dict()

    conf["channel_name"] = channel_name
    conf["slack_channel_name"] = "fortestchannel" #TODO change it is harcoded here
    conf["slack_access_token"] = auth_response['access_token']
    conf["slack_token_expiration_date"] = (datetime.now() + timedelta(hours=24*365)).__str__()

    SlackTokens.put_token(SlackTokens, channel_name, conf)
    return conf


def auto_auth(url, channel_id):
    return redirect(url)

def post_pre_validation(post):
    return 1;


def share_post ( channel_name,slack_channel_name, text , link) :

    token = SlackTokens.get_token(SlackTokens, channel_name).__getitem__(0)
    slack_channel_name = slack_channel_name

    print('share_post token ', token)
    sc = SlackClient(token)

    sc.api_call(
        "chat.postMessage",
        channel=slack_channel_name,
        text=text
    )



def run(publishing, channel_config):

    channel_config= json.loads(channel_config);
    print("publishing slack", publishing)
    print("channel-conf", type(channel_config), channel_config)
    print("conf run", channel_config, type(channel_config))
    channel_name = channel_config['channel_name']
    slack_channel_name = channel_config['slack_channel_name']
    authenticate(channel_name, (publishing.post_id, publishing.channel_id))
    share_post(channel_name, slack_channel_name,publishing.description,None)


@slack_verify_callback_page.route("/slack/verify", methods=['GET'])
def slack_verify_authorization():

    # Retrieve the auth code from the request params
    auth_code = request.args['code']
    conf_publishing = json.loads(request.args.get('state'))
    channel_name = conf_publishing['channel_name']
    publishing_id = conf_publishing['publishing_id']
    post_id = publishing_id.__getitem__(0)
    channel_id = publishing_id.__getitem__(1)
    print(auth_code)

    if auth_code :
        channel_config = set_access_token(channel_name, auth_code)

    print("channel_config", channel_config)
    # normally should redirect to the channel page or to the page that publish a post
    publishing = Publishing.query.filter_by(post_id=post_id, channel_id=channel_id).first()
    print("init publishing", publishing)
    run(publishing, json.dumps(channel_config))

    return redirect(url_for('index'))


class SlackTokens:

    def get_token(self, channel_name):

        channel = Channel.query.filter_by(name=channel_name, module=get_module_full_name("slack")).first()

        if channel and channel.config:
            conf = json.loads(channel.config)
            date_string = conf.get("slack_token_expiration_date")

            if not date_string :
                return (None, None)

            date_expiration = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
            print("date_expiration", conf.get("slack_access_token"), date_expiration)
            return (conf.get("slack_access_token"), date_expiration)

        return (None, None)

    def put_token(self, channel_name, config_json):
        print("type config json : -> ",type(config_json))
        c = Channel.query.filter_by(name=channel_name, module=get_module_full_name("slack")).first()
        c.config = json.dumps(config_json)
        print("put token", config_json)
        db.session.commit()