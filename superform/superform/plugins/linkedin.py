import json

from flask import redirect, url_for, request, Blueprint
from linkedin import linkedin
from superform.suputils import selenium_utils
from datetime import datetime, timedelta
from superform.suputils import plugin_utils

from superform.models import db, Channel, Publishing, State
from superform.suputils import keepass

linkedin_verify_callback_page = Blueprint('linkedin', 'channels')

FIELDS_UNAVAILABLE = []
CONFIG_FIELDS = ["channel_name", "linkedin_access_token", "linkedin_token_expiration_date"]
AUTH_FIELDS = True
POST_FORM_VALIDATIONS = {
    'title_max_length': 200,
    'description_max_length': 256,
    'image_type': 'url'
}
API_KEY = keepass.get_password_from_keepass('linkedin_key')
API_SECRET = keepass.get_password_from_keepass('linkedin_secret')
RETURN_URL = keepass.get_username_from_keepass('linkedin_return_url')

authentication = linkedin.LinkedInAuthentication(
    API_KEY,
    API_SECRET,
    RETURN_URL,
    ['r_basicprofile', 'r_emailaddress', 'w_share', 'rw_company_admin']
)


def authenticate(channel_id, publishing_id):
    """
    Try to authenticate a channel based on channel_id
    :param channel_id: Channel we try to authenticate
    :param publishing_id: Publishing we want to publish on channel
    :return: The authorization url if the channel token is absent or has expired else return 'AlreadyAuthenticated'
    """
    previous_token = LinkedinTokens.get_token(LinkedinTokens, channel_id)

    channel_name = Channel.query.get(channel_id).name

    if previous_token.__getitem__(0) is None or (datetime.now() > previous_token.__getitem__(1)):
        conf = dict()
        conf["channel_name"] = channel_name
        conf["publishing_id"] = publishing_id

        authentication.state = json.dumps(conf)
        print("authorization_url", authentication.authorization_url)
        return authentication.authorization_url  # open this url on your browser
    else:
        return 'AlreadyAuthenticated'


def set_access_token(channel_id, code):
    """
    Bind access token with channel based on code and channel_id
    :param channel_id: Channel we want to bind the token to
    :param code: Contained in the callback response from linkedin
    :return: channel_id config containing the token and expiration date
    """
    authentication.authorization_code = code
    result = authentication.get_access_token()

    channel = Channel.query.get(channel_id)
    channel_name = channel.name
    # add the configuration to the channel
    conf = json.loads(channel.config)
    conf["channel_name"] = channel_name
    conf["linkedin_access_token"] = result.access_token
    conf["linkedin_token_expiration_date"] = (datetime.now() + timedelta(seconds=result.expires_in)).__str__()
    
    LinkedinTokens.put_token(LinkedinTokens, channel_id, conf)
    return conf


def share_post(channel_id, comment, title, submitted_url, submitted_image_url, visibility_code):
    """
    Publish a message on a linkedin channel,
    :param channel_id: The id of the channel we want to publish to
    :param comment:  The description of the post
    :param title: The title of the post
    :param submitted_url: The link contained in the post
    :param submitted_image_url: The image contained in the post
    :param visibility_code: Describe who can see this post
    :return: True if the message is published else False
    """
    token = LinkedinTokens.get_token(LinkedinTokens, channel_id).__getitem__(0)
    print('share_post token ', token)
    application = linkedin.LinkedInApplication(token=token)
    print('submitted_url', submitted_url)
    if submitted_url is '':
        submitted_url = None
    if submitted_image_url is '':
        submitted_image_url = None

    application.submit_share(comment=comment, title=title, submitted_url=submitted_url,
                             submitted_image_url=submitted_image_url, description="This is a sharing from Superform",visibility_code=visibility_code)
    return True


def auto_auth(url, channel_id):
    """
    :param url: url of the authentication page
    :param channel_id: channel we try to authenticate
    :return: A redirection to home if successful otherwise a redirection to an error page
    """
    if keepass.set_entry_from_keepass(str(channel_id)) is 0:
        print('Error : cant get keepass entry :', str(channel_id), 'for linkedin plugin')
        return redirect(url_for('keepass.error_channel_keepass', chan_id=channel_id))

    driver = selenium_utils.get_headless_chrome()

    driver.get(url)
    username = driver.find_element_by_name("session_key")
    password = driver.find_element_by_name("session_password")

    username.send_keys(keepass.KeepassEntry.username)
    password.send_keys(keepass.KeepassEntry.password)

    driver.find_element_by_name("signin").click()

    if not selenium_utils.wait_redirect(driver, 'linkedin'):
        driver.close()
        return redirect(url_for('keepass.error_channel_keepass', chan_id=channel_id))

    driver.close()
    return redirect(url_for('index'))


def run(publishing, channel_config):
    """
    Publish a Publishing on a channel
    :param publishing: The publishing we want to publish
    :param channel_config: The channel config of the channel we want to publish on
    :return:
    """
    print("publishing Linkedin", publishing)
    print("channel-conf", type(channel_config), channel_config)
    print("conf run", channel_config, type(channel_config))
    authenticate(publishing.channel_id, (publishing.post_id, publishing.channel_id))

    if share_post(publishing.channel_id, publishing.description, publishing.title, publishing.link_url, publishing.image_url, "anyone"):
        publishing.state = State.VALIDATED_SHARED.value
        db.session.commit()


def post_pre_validation(post):
    """
    Validate a post to be published with this linkedin
    :param post: The Post we try to validate
    :return: True if the post is valid for this module else False
    """
    return plugin_utils.post_pre_validation_plugins(post,200,256)


class LinkedinTokens:

    def get_token(self, channel_id):

        channel = Channel.query.get(channel_id)

        if channel and channel.config:
            print("put token", channel.config)
            conf = json.loads(channel.config)
            date_string = conf.get("linkedin_token_expiration_date")

            if date_string == "None" or date_string is None:
                return (None, None)

            date_expiration = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
            print("date_expiration", conf.get("linkedin_access_token"), date_expiration)
            return (conf.get("linkedin_access_token"), date_expiration)

        return (None, None)

    def put_token(self, channel_id, config_json):
        c = Channel.query.get(channel_id)
        c.config = json.dumps(config_json)
        print("put token", config_json)
        db.session.commit()


@linkedin_verify_callback_page.route("/linkedin/verify", methods=['GET'])
def linkedin_verify_authorization():
    code = request.args.get('code')
    conf_publishing = json.loads(request.args.get('state'))
    channel_name = conf_publishing['channel_name']
    publishing_id = conf_publishing['publishing_id']
    post_id = publishing_id.__getitem__(0)
    channel_id = publishing_id.__getitem__(1)
    print("code", code)
    print("post id, channel id", post_id, channel_id)
    channel_config = {}
    if code:
        channel_config = set_access_token(channel_id,code)
    print("channel_config", channel_config)
    #normally should redirect to the channel page or to the page that publish a post
    publishing = Publishing.query.filter_by(post_id=post_id, channel_id=channel_id).\
        order_by(Publishing.num_version.desc()).first()
    print("init publishing", publishing)
    run(publishing, json.dumps(channel_config))
    return redirect(url_for('index'))
