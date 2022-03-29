clubhouse.py

load_config
section_key_exception
config_to_dict
config_to_list
reload_client
unstable_endpoint

Clubhouse:
	
Auth:
	start(self, phone_number)
	resend(self, phone_number)
	complete(self, phone_number, rc_token, verification_code)
	logout(self)	

Client:
	me(self, return_blocked_ids=False, timezone_identifier="Asia/Tokyo", return_following_ids=False)
	feed(self)
	profile(self, client_id='', username='')
	ping_user(self, channel, user_id)
	following
	followers
	search
	get_clubs
	get_online_friends
	get_settings
	add_email
	add_topic
	remove_topic
	update_photo
	update_bio
	update_name
	update_username
	update_displayname
	update_twitter_username
	update_instagram_username
	update_skintone
	update_follow_notifications
	refresh_token
	report_incident

User:
    get_profile(self, user_id='', username='')
    follow(self, user_id, user_ids=None, source=4, source_topic_id=None)
	unfollow(self, user_id)
    follow_multiple(self, user_ids, user_id=None, source=7, source_topic_id=None)
    following(self, user_id, page_size=50, page=1)
    followers(self, user_id, page_size=50, page=1)
    mutual_follows(self, user_id, page_size=50, page=1)
    block(self, user_id)
    get_events_for_user(self, user_id='', page_size=25, page=1)

Notifications:
    get(self, page_size=20, page=1)
    get_actionable(self)
    ignore_actionable(self, actionable_notification_id)

Channel:
    get(self, channel, channel_id=None)
    def join(self, channel, attribution_source="feed", attribution_details="eyJpc19leHBsb3JlIjpmYWxzZSwicmFuayI6MX0=")
    audience_reply(self, channel, raise_hands=True, unraise_hands=False)
    accept_speaker_invite(self, channel, client_id)
    reject_speaker_invite(self, channel, client_id)
    update_audio_mode(self, channel)
    active_ping(self, channel)
    leave(self, channel)
    create(self, topic="", user_ids=(), is_private=False, is_social_mode=False)
    invite_to_new_channel(self, user_id, channel)
    accept_new_channel_invite(self, channel_invite_id)
    reject_new_channel_invite(self, channel_invite_id)
    cancel_new_channel_invite(self, channel_invite_id)
    hide(self, channel, hide=True)
    get_create_channel_targets(self)

ChannelMod:
    make_moderator(self, channel, user_id)
    invite_speaker(self, channel, user_id)
    uninite_speaker(self, channel, user_id)
    add_link(self, channel, link)
    remove_link(self, channel)
    make_public(self, channel, channel_id=None)
    make_social(self, channel, channel_id=None)
    end(self, channel, channel_id=None)
    remove_user(self, channel, user_id)
    change_handraising(self, channel, is_enabled=True, handraise_permission=1)

ChannelChat:
    get(self, channel)
    send(self, channel, message)

Message:
    get_feed(self)
	create(self, participant_ids)
    search_(self, participant_ids)
	get_message(self, chat_id)
    get_message_thread(self, participant_ids)
    get_message_id(self, participant_ids)
    send(self, message, chat_id=None, participant_ids=None)

Event:
    get(self, event_id=None, user_ids=None, club_id=None, is_member_only=False, event_hashid=None, description=None, time_start_epoch=None, name=None)
    create(self, name, time_start_epoch, description, event_id=None, user_ids=(), club_id=None, is_member_only=False, event_hashid=None)
    edit(self, name, time_start_epoch, description, event_id=None, user_ids=(), club_id=None, is_member_only=False, event_hashid=None)
    delete(self, event_id, user_ids=None, club_id=None, is_member_only=False, event_hashid=None, description=None, time_start_epoch=None, name=None)
    get_events(self, is_filtered=True, page_size=25, page=1)
    get_events_to_start(self)
    get_events_for_user(self, user_id='', page_size=25, page=1)

Club:
    get(self, club_id, source_topic_id=None)
    get_members(self, club_id, return_followers=False, return_members=True, page_size=50, page=1)
    join(self, club_id, source_topic_id=None)
    leave(self, club_id, source_topic_id=None)
    add_club_admin(self, club_id, user_id)
    remove_club_admin(self, club_id, user_id)
    remove_club_member(self, club_id, user_id)
    accept_club_member_invite(self, club_id, source_topic_id=None, invite_code=None)
    add_club_member(self, club_id, user_id, name, phone_number, message, reason)
    get_club_nominations(self, club_id, source_topic_id)
    approve_club_nomination(self, club_id, source_topic_id, invite_nomination_id)
    reject_club_nomination(self, club_id, source_topic_id, invite_nomination_id)
    add_club_topic(self, club_id, topic_id)
    remove_club_topic(self, club_id, topic_id)
    update_is_follow_allowed(self, club_id, is_follow_allowed=True)
    update_is_membership_private(self, club_id, is_membership_private=False)
    update_is_community(self, club_id, is_community=False)
    update_club_description(self, club_id, description)
    update_club_rules(self, club_id='', rules=())

Topic:

    get_all_topics(self)
    get_topic(self, topic_id)
    get_users_for_topic(self, topic_id, page_size=25, page=1)
    get_clubs_for_topic(self, topic_id, page_size=25, page=1)










