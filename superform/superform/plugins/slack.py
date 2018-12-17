from datetime import datetime, timedelta
from flask import flash, Blueprint, redirect, url_for, request, render_template
from slackclient import SlackClient
import json
from superform.models import Channel, Publishing, db, State
from superform.suputils import keepass, selenium_utils, plugin_utils

FIELDS_UNAVAILABLE = ['Publication Date']
CONFIG_FIELDS = ["channel_name", "slack_channel_name", "slack_domain_name", "slack_access_token",
                 "slack_token_expiration_date"]
AUTH_FIELDS = True

POST_FORM_VALIDATIONS = {
    'title_max_length': 40000,
    'description_max_length': 40000,
    'image_type': 'url'
}

API_CLIENT_KEY = keepass.get_password_from_keepass('slack_client_key')
API_SECRET = keepass.get_password_from_keepass('slack_secret')
API_CLIENT_ID = keepass.get_password_from_keepass('slack_client_id')

slack_error_callback_page = Blueprint('slack_error', 'channels')
slack_verify_callback_page = Blueprint('slack', 'channels')

slackClient = SlackClient()


def authenticate(channel_id, publishing_id):
    """
    Try to authenticate a channel based on channel_id
    :param channel_id: Channel we try to authenticate
    :param publishing_id: Publishing we want to publish on channel
    :return: The authorization url if the channel token is absent or has expired else return 'AlreadyAuthenticated'
    """
    previous_token = SlackTokens.get_token(SlackTokens, channel_id)
    channel_name = Channel.query.get(channel_id).name

    if previous_token.__getitem__(0) is None or (datetime.now() > previous_token.__getitem__(1)):

        conf = dict()
        conf["channel_name"] = channel_name
        conf["publishing_id"] = publishing_id

        state = json.dumps(conf)
        return "https://slack.com/oauth/authorize?scope=identity.basic&client_id=" + API_CLIENT_ID + "&state=" + state  # open this url on your browser
    else:
        return 'AlreadyAuthenticated'


def set_access_token(channel_id, code):
    """
    Bind access token with channel based on code and channel_id
    :param channel_id: Channel we want to bind the token to
    :param code: Contained in the callback response from slack
    :return: channel_id config containing the token and expiration date
    """
    # An empty string is a valid token for this request
    sc = SlackClient("")

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        "oauth.access",
        client_id=API_CLIENT_ID,
        client_secret=API_SECRET,
        code=code
    )

    channel = Channel.query.get(channel_id)
    channel_name = channel.name
    # add the configuration to the channel
    conf = json.loads(channel.config)
    conf["channel_name"] = channel_name
    conf["slack_access_token"] = auth_response['access_token']
    conf["slack_token_expiration_date"] = (datetime.now() + timedelta(hours=24 * 365)).__str__()

    SlackTokens.put_token(SlackTokens, channel_id, conf)
    return conf


def auto_auth(url, channel_id):
    """
    :param url: url of the authentication page
    :param channel_id: channel we try to authenticate
    :return: A redirection to home if successful otherwise a redirection to an error page
    """
    if keepass.set_entry_from_keepass(str(channel_id)) is 0:
        print('Error : cant get keepass entry :', str(channel_id), 'for slack plugin')
        return redirect(url_for('keepass.error_channel_keepass', chan_id=channel_id))

    conf = Channel.query.get(channel_id).config
    if not conf or conf == '{}':
        return redirect(url_for('slack_error.error_config_slack', chan_id=channel_id))

    dom = json.loads(conf)['slack_domain_name']

    if dom == 'None' or dom == '':
        return redirect(url_for('slack_error.error_config_slack', chan_id=channel_id))

    driver = selenium_utils.get_headless_chrome()
    driver.get(url)
    domain = driver.find_element_by_name("domain")
    domain.send_keys(dom)
    driver.find_element_by_css_selector('button[id="submit_team_domain"]').click()

    if not selenium_utils.wait_redirect(driver, 'signin'):
        driver.close()
        return redirect(url_for('slack_error.error_config_slack', chan_id=channel_id))

    email = driver.find_element_by_name("email")
    password = driver.find_element_by_name("password")
    email.send_keys(keepass.KeepassEntry.username)
    password.send_keys(keepass.KeepassEntry.password)
    driver.find_element_by_css_selector('button[id="signin_btn"]').click()

    if not selenium_utils.wait_redirect_after(driver, 'testlingi2255team8.slack.com/oauth'):
        driver.close()
        return redirect(url_for('keepass.error_channel_keepass', chan_id=channel_id))

    driver.find_element_by_css_selector('button[id="oauth_authorizify"]').click()

    if not selenium_utils.wait_redirect(driver, 'testlingi2255team8.slack.com'):
        driver.close()
        return redirect(url_for('slack_error.error_config_slack', chan_id=channel_id))

    driver.close()
    return redirect(url_for('index'))


def post_pre_validation(post):
    """
    Validate a post to be published with this slack
    :param post: The Post we try to validate
    :return: True if the post is valid for this module else False
    """
    return plugin_utils.post_pre_validation_plugins(post, 40000, 40000)


def share_post(channel_id, slack_channel_name, title, description, link, link_image):
    """
    Publish a message on a slack channel,
    :param channel_id: The id of the channel we want to publish to
    :param slack_channel_name:  The name of the slack channel we want to publish to (the channel on slack server)
    :param title: The title of the post
    :param description:  The description of the post
    :param link: The link contained in the post
    :param link_image: The image contained in the post
    :return: True if the message is published else False
    """
    token = SlackTokens.get_token(SlackTokens, channel_id).__getitem__(0)

    print('slack_channel_nam  ', slack_channel_name)
    sc = SlackClient(token)
    res = sc.api_call(
        "chat.postMessage",
        channel=slack_channel_name,
        attachments=[
            {
                "pretext": title,
                "title": link,
                "title_link": link,
                "image_url": link_image,
                "text": description
            }
        ]
    )
    print("res share post", res)
    if not res['ok']:
        print("Error", res["error"])
        flash("Error " + ' '.join(res["error"].split('_')))
        return False
    return True


def run(publishing, channel_config):
    """
    Publish a Publishing on a channel
    :param publishing: The publishing we want to publish
    :param channel_config: The channel config of the channel we want to publish on
    :return:
    """
    channel_config = json.loads(channel_config);
    print("publishing slack", publishing)
    print("channel-conf", type(channel_config), channel_config)
    print("conf run", channel_config, type(channel_config))
    slack_channel_name = channel_config['slack_channel_name']

    authenticate(publishing.channel_id, (publishing.post_id, publishing.channel_id))
    if share_post(publishing.channel_id, slack_channel_name, publishing.title, publishing.description, publishing.link_url,
                  publishing.image_url):
        publishing.state = State.VALIDATED_SHARED.value
        db.session.commit()


@slack_verify_callback_page.route("/slack/verify", methods=['GET'])
def slack_verify_authorization():
    # Retrieve the auth code from the request params
    auth_code = request.args['code']
    conf_publishing = json.loads(request.args.get('state'))
    publishing_id = conf_publishing['publishing_id']
    post_id = publishing_id.__getitem__(0)
    channel_id = publishing_id.__getitem__(1)
    print(auth_code)

    if auth_code:
        channel_config = set_access_token(channel_id, auth_code)

    print("channel_config", channel_config)
    # normally should redirect to the channel page or to the page that publish a post
    publishing = Publishing.query.filter_by(post_id=post_id, channel_id=channel_id).\
        order_by(Publishing.num_version.desc()).first()
    print("init publishing", publishing)
    run(publishing, json.dumps(channel_config))

    return redirect(url_for('index'))


class SlackTokens:

    def get_token(self, channel_id):

        channel = Channel.query.get(channel_id)

        if channel and channel.config:
            print('channel.config', channel.config)
            conf = json.loads(channel.config)
            date_string = conf.get("slack_token_expiration_date")

            if not date_string or date_string is None or date_string == "None":
                return (None, None)

            date_expiration = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
            print("date_expiration", conf.get("slack_access_token"), date_expiration)
            return (conf.get("slack_access_token"), date_expiration)

        return (None, None)

    def put_token(self, channel_id, config_json):
        print("type config json : -> ", type(config_json))
        c = Channel.query.get(channel_id)
        c.config = json.dumps(config_json)
        print("put token", config_json)
        db.session.commit()


@slack_error_callback_page.route('/error_config_slack/<int:chan_id>')
def error_config_slack(chan_id):
    chan_name = Channel.query.get(chan_id).name
    return render_template('error_config_slack.html', channel=chan_name)
