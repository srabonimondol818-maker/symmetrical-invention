#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 CINEFLIX ULTIMATE BOT
Premium Video Bot with Full Admin Panel + Enhanced Features
"""

import os
import sys
import logging
import html
import string
import random
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ChatJoinRequestHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# ===================== CONFIGURATION =====================
# All sensitive data from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = os.getenv("ADMIN_ID")

# Validate required environment variables
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable not set!")
    sys.exit(1)

if not MONGO_URI:
    print("❌ ERROR: MONGO_URI environment variable not set!")
    sys.exit(1)

if not ADMIN_ID:
    print("❌ ERROR: ADMIN_ID environment variable not set!")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ERROR: ADMIN_ID must be a number!")
    sys.exit(1)

# ===================== LOGGING SETUP =====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== MONGODB SETUP =====================
try:
    logger.info("🔄 Connecting to MongoDB...")
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db = mongo_client['cineflix_bot']
    
    # Collections
    videos_col = db['videos']
    force_join_col = db['force_join_channels']
    users_col = db['users']
    settings_col = db['settings']
    messages_col = db['messages']
    buttons_col = db['buttons']
    pending_requests_col = db['pending_join_requests']  # Track join requests
    verified_channels_col = db['verified_video_channels']  # 🔥 NEW: Verified channels only
    direct_videos_col = db['direct_videos']  # Direct bot upload videos
    forward_channels_col = db['forward_channels']  # Multiple forward channels
    voice_channels_col = db['voice_channels']  # 🎙️ Voice Manager channels
    post_manager_channels_col = db['post_manager_channels']  # 📢 Post Manager channels
    pinned_buttons_col = db['pinned_buttons']  # 📌 Pinned message buttons
    pending_posts_col = db['pending_posts']  # Posts waiting for admin action
    
    logger.info("✅ MongoDB Connected Successfully!")
    
except (ConnectionFailure, OperationFailure) as e:
    logger.error(f"❌ MongoDB Connection Failed: {e}")
    logger.error("Bot cannot run without database. Please check MONGO_URI.")
    sys.exit(1)

# Admin state tracking
admin_states = {}

# Track user's last video request messages (to delete duplicates)
user_video_messages = {}  # Format: {user_id: {video_id: [message_ids]}}

# NEW: Track user's ALL messages for cleanup (not just video-specific)
user_all_messages = {}  # Format: {user_id: [message_ids]}

# ===================== DEFAULT MESSAGES =====================
DEFAULT_MESSAGES = {
    'welcome': """🎬 **Welcome to CINEFLIX, {name}!** 👋

Movies · Series · Web Series · Anime · Exclusive — সব এক জায়গায়!

━━━━━━━━━━━━━━━━━━━━
**🚀 কীভাবে শুরু করবেন?**

**①** নিচে **"🎮 Open CINEFLIX App"** চাপুন
**②** পছন্দের কন্টেন্ট বেছে নিন
**③** প্রথমবার চ্যানেল জয়েন করুন
**④** Enjoy! 🍿
━━━━━━━━━━━━━━━━━━━━
✅ HD Quality · ✅ Daily Updates · ✅ Free to Watch""",

    'help': """📚 **CINEFLIX — Help**

**Commands:**
/start — App খুলুন
/help — এই মেনু

**ভিডিও দেখার নিয়ম:**
① App থেকে পছন্দের ভিডিও চাপুন
② চ্যানেল জয়েন করুন (প্রথমবার)
③ Enjoy! 🍿

**সমস্যা হলে:**
• লিঙ্ক কাজ না করলে — App রিফ্রেশ করুন
• ভিডিও না এলে — চ্যানেল জয়েন চেক করুন
• অন্য সমস্যায় — Admin-কে মেসেজ করুন""",

    'force_join': """🔒 **ভিডিওটি আনলক করতে চ্যানেল জয়েন করুন**

নিচের বাটনে ক্লিক করুন → Join/Request করুন → **"✅ I Joined"** চাপুন।

💡 **Private channel?** শুধু Request পাঠান — Approve-এর দরকার নেই!""",

    'after_video': """🍿 **ভিডিও উপভোগ করুন!**

আরও হাজারো কন্টেন্ট দেখতে নিচের বাটন চাপুন। প্রতিদিন নতুন আপডেট! 🎬""",

    'video_not_found': """❌ **ভিডিওটি পাওয়া যাচ্ছে না**

লিঙ্কটি মেয়াদ উত্তীর্ণ হয়ে গেছে বা সরিয়ে নেওয়া হয়েছে।

👉 App-এ ফিরে অন্য কন্টেন্ট দেখুন — প্রতিদিন নতুন আপডেট!""",

    'auto_reply': """👋 **Hello!**

আমি CINEFLIX Bot — Movies, Series, Anime সব এখানে! 🎬

নিচের বাটন চেপে App খুলুন অথবা /start করুন।""",

    # 🔥 ULTIMATE PREMIUM MESSAGES (Auto-update force join)
    'force_join_start': """🔐 **Unlock Your Video**

Hey **{name}**! 👋

**Join {count} channel{plural} to unlock:**

{channels_list}

💡 Tap channels → Send requests → Auto-unlock!""",

    'force_join_progress': """✅ **{joined_name} Joined!**

Great! 🎉 **{remaining} more to go!**

{channels_list}""",

    'force_join_almost': """✅ **{joined_name} Joined!**

Almost there! 💪 **Just 1 more!**

{channels_list}""",

    'force_join_complete': """🎉 **All Channels Joined!**

Perfect! Unlocking your video...""",

    'video_unlocked': """🎬 **{video_title}**

Enjoy! 🍿"""
}

DEFAULT_SETTINGS = {
    'mini_app_url': 'https://cinaflix-streaming.vercel.app/',
    'main_channel_id': -1003872857468,
    'main_channel_username': 'Cinaflixsteem',
    'video_protection': True,
    'bot_name': 'CINEFLIX',
    'auto_reply_enabled': True,
    'message_cleanup_enabled': True,
    'welcome_media_enabled': False,  # NEW: Welcome GIF/Video
    'welcome_media_file_id': None,   # NEW: Telegram file_id
    'welcome_media_type': None,      # NEW: 'photo', 'animation', 'video'
    'folder_link_enabled': False,       # NEW: Enable folder join link
    'folder_link_url': '',              # NEW: Telegram folder link (https://t.me/addlist/xxxxx)
    'video_not_found_button': True,     # NEW: Show Mini App button on video not found
    'welcome_voice_enabled': False,     # 🎙️ Welcome Voice: ON/OFF
    'welcome_voice_file_id': None,      # 🎙️ Welcome Voice: Telegram file_id
}

# ===================== DATABASE HELPER FUNCTIONS =====================

# ===================== 🔥 FORWARD CHANNELS DB HELPERS =====================

def get_forward_channels():
    """Get all active forward channels"""
    try:
        return list(forward_channels_col.find({'is_active': True}))
    except Exception as e:
        logger.error(f"Error getting forward channels: {e}")
        return []

def add_forward_channel(channel_id, channel_name):
    """Add a forward channel"""
    try:
        forward_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'is_active': True,
                'enabled': True,  # Toggle: True=forward হবে, False=হবে না
                'added_at': datetime.utcnow()
            }},
            upsert=True
        )
        logger.info(f"✅ Forward channel added: {channel_name} ({channel_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding forward channel: {e}")
        return False

def toggle_forward_channel(channel_id):
    """Toggle a forward channel on/off"""
    try:
        ch = forward_channels_col.find_one({'channel_id': channel_id, 'is_active': True})
        if not ch:
            return None
        new_val = not ch.get('enabled', True)
        forward_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {'enabled': new_val}}
        )
        return new_val  # returns new state
    except Exception as e:
        logger.error(f"Error toggling forward channel: {e}")
        return None

def remove_forward_channel(channel_id):
    """Remove a forward channel"""
    try:
        result = forward_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error removing forward channel: {e}")
        return False

def get_forward_channel_count():
    """Count active forward channels"""
    try:
        return forward_channels_col.count_documents({'is_active': True})
    except Exception as e:
        logger.error(f"Error counting forward channels: {e}")
        return 0


def get_setting(key, default=None):
    """Get setting from database"""
    try:
        setting = settings_col.find_one({'key': key})
        return setting['value'] if setting else default
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return default

def set_setting(key, value):
    """Set setting in database"""
    try:
        settings_col.update_one(
            {'key': key},
            {'$set': {'key': key, 'value': value, 'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting {key}: {e}")
        return False

def get_message(key):
    """Get message template from database"""
    try:
        msg = messages_col.find_one({'key': key})
        return msg['text'] if msg else DEFAULT_MESSAGES.get(key, '')
    except Exception as e:
        logger.error(f"Error getting message {key}: {e}")
        return DEFAULT_MESSAGES.get(key, '')

def set_message(key, text):
    """Set message template in database"""
    try:
        messages_col.update_one(
            {'key': key},
            {'$set': {'key': key, 'text': text, 'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting message {key}: {e}")
        return False

def initialize_defaults():
    """Initialize default settings and messages if not exists"""
    try:
        # Initialize settings
        for key, value in DEFAULT_SETTINGS.items():
            if not settings_col.find_one({'key': key}):
                set_setting(key, value)
        
        # Initialize messages
        for key, text in DEFAULT_MESSAGES.items():
            if not messages_col.find_one({'key': key}):
                set_message(key, text)
        
        # 🔥 MongoDB Indexes for performance (safe to run multiple times)
        try:
            users_col.create_index('user_id', unique=True, background=True)
            users_col.create_index('last_active', background=True)
            videos_col.create_index('message_id', unique=True, background=True)
            videos_col.create_index('channel_id', background=True)
            videos_col.create_index('saved_at', background=True)
            direct_videos_col.create_index('code', unique=True, background=True)
            direct_videos_col.create_index('created_at', background=True)
            force_join_col.create_index('channel_id', unique=True, background=True)
            verified_channels_col.create_index('channel_id', unique=True, background=True)
            forward_channels_col.create_index('channel_id', unique=True, background=True)
            pending_requests_col.create_index([('user_id', 1), ('channel_id', 1)], background=True)
            logger.info("✅ MongoDB indexes created/verified")
        except Exception as idx_err:
            logger.warning(f"Index creation warning (non-critical): {idx_err}")
        
        logger.info("✅ Default settings and messages initialized")
    except Exception as e:
        logger.error(f"Error initializing defaults: {e}")

def save_video(channel_id, message_id, channel_name="Main", media_type="video"):
    """Save video/photo/animation to database"""
    try:
        video_data = {
            'channel_id': channel_id,
            'message_id': message_id,
            'channel_name': channel_name,
            'media_type': media_type,  # NEW: 'video', 'photo', 'animation', 'document'
            'saved_at': datetime.utcnow(),
            'views': 0
        }
        videos_col.update_one(
            {'channel_id': channel_id, 'message_id': message_id},
            {'$set': video_data},
            upsert=True
        )
        logger.info(f"✅ {media_type.title()} saved: {channel_name} - {message_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving {media_type}: {e}")
        return False

def get_video(message_id):
    """Get video from database"""
    try:
        return videos_col.find_one({'message_id': int(message_id)})
    except Exception as e:
        logger.error(f"Error getting video: {e}")
        return None

def increment_video_view(message_id):
    """Increment video view count"""
    try:
        videos_col.update_one(
            {'message_id': int(message_id)},
            {'$inc': {'views': 1}}
        )
    except Exception as e:
        logger.error(f"Error incrementing view: {e}")

def add_force_join_channel(channel_id, username, invite_link=None, display_name=None):
    """Add force join channel with optional invite link for private channels"""
    try:
        # Auto-number display_name if not provided
        if not display_name:
            count = force_join_col.count_documents({'is_active': True})
            display_name = f"Channel {count + 1}"

        channel_data = {
            'channel_id': channel_id,
            'username': username.replace('@', ''),
            'display_name': display_name,   # ← NEW: Button display name
            'invite_link': invite_link,
            'added_at': datetime.utcnow(),
            'is_active': True
        }
        force_join_col.update_one(
            {'channel_id': channel_id},
            {'$set': channel_data},
            upsert=True
        )
        
        link_info = f" (invite: {invite_link})" if invite_link else ""
        logger.info(f"✅ Force join channel added: {display_name} @{username}{link_info}")
        return True
    except Exception as e:
        logger.error(f"Error adding force join channel: {e}")
        return False

def remove_force_join_channel(channel_id):
    """Remove force join channel"""
    try:
        result = force_join_col.delete_one({'channel_id': channel_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing force join channel: {e}")
        return False

def get_force_join_channels():
    """Get all active force join channels"""
    try:
        return list(force_join_col.find({'is_active': True}))
    except Exception as e:
        logger.error(f"Error getting force join channels: {e}")
        return []

def save_user(user_id, username, first_name):
    """Save user to database"""
    try:
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_active': datetime.utcnow()
        }
        users_col.update_one(
            {'user_id': user_id},
            {'$set': user_data, '$setOnInsert': {'first_seen': datetime.utcnow()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving user: {e}")

def get_stats():
    """Get bot statistics"""
    try:
        # Basic stats
        total_users = users_col.count_documents({})
        total_videos = videos_col.count_documents({})
        total_force_join = force_join_col.count_documents({'is_active': True})
        total_verified = verified_channels_col.count_documents({'is_active': True})  # 🔥 NEW
        
        # Active users (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_today = users_col.count_documents({
            'last_active': {'$gte': yesterday}
        })
        
        # Most viewed video
        top_video = videos_col.find_one(sort=[('views', -1)])
        top_views = top_video['views'] if top_video else 0
        
        return {
            'users': total_users,
            'videos': total_videos,
            'force_join': total_force_join,
            'verified_channels': total_verified,  # 🔥 NEW
            'active_today': active_today,
            'top_views': top_views
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            'users': 0,
            'videos': 0,
            'force_join': 0,
            'verified_channels': 0,  # 🔥 NEW
            'active_today': 0,
            'top_views': 0
        }

def get_all_users():
    """Get all user IDs for broadcasting"""
    try:
        users = users_col.find({}, {'user_id': 1})
        return [user['user_id'] for user in users]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

def get_buttons(location):
    """Get buttons for a specific location (welcome or after_video)"""
    try:
        buttons = list(buttons_col.find({'location': location, 'is_active': True}).sort('order', 1))
        return buttons
    except Exception as e:
        logger.error(f"Error getting buttons for {location}: {e}")
        return []

def add_button(location, text, url, button_type='url', order=0):
    """Add a custom button"""
    try:
        button_data = {
            'location': location,  # 'welcome' or 'after_video'
            'text': text,
            'url': url,
            'type': button_type,  # 'url' or 'web_app'
            'order': order,
            'is_active': True,
            'created_at': datetime.utcnow()
        }
        result = buttons_col.insert_one(button_data)
        logger.info(f"✅ Button added: {text} at {location}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error adding button: {e}")
        return None

def remove_button(button_id):
    """Remove a button"""
    try:
        from bson.objectid import ObjectId
        result = buttons_col.delete_one({'_id': ObjectId(button_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing button: {e}")
        return False

# ===================== PENDING JOIN REQUEST HELPERS =====================
def mark_join_request_sent(user_id, channel_id):
    """Mark that user has sent a join request to a channel"""
    try:
        pending_requests_col.update_one(
            {'user_id': user_id, 'channel_id': channel_id},
            {
                '$set': {
                    'user_id': user_id,
                    'channel_id': channel_id,
                    'requested_at': datetime.utcnow(),
                    'status': 'pending'
                }
            },
            upsert=True
        )
        logger.info(f"✅ Marked join request: user {user_id} -> channel {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Error marking join request: {e}")
        return False

def mark_join_approved(user_id, channel_id):
    """Mark join request as approved (bot auto-approved)"""
    try:
        pending_requests_col.update_one(
            {'user_id': user_id, 'channel_id': channel_id},
            {
                '$set': {
                    'user_id': user_id,
                    'channel_id': channel_id,
                    'status': 'approved',
                    'approved_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"✅ Marked join approved: user {user_id} -> channel {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Error marking join approved: {e}")
        return False

def has_pending_join_request(user_id, channel_id):
    """
    Check if user has access via join request (pending OR approved by bot).
    Both statuses grant access — approved = bot already approved them.
    """
    try:
        request = pending_requests_col.find_one({
            'user_id': user_id,
            'channel_id': channel_id,
            'status': {'$in': ['pending', 'approved']}
        })
        return request is not None
    except Exception as e:
        logger.error(f"Error checking pending request: {e}")
        return False

def revoke_join_access(user_id, channel_id):
    """Remove join access — call this if admin removes user from channel"""
    try:
        pending_requests_col.delete_one({'user_id': user_id, 'channel_id': channel_id})
        logger.info(f"🗑️ Revoked join access: user {user_id} -> channel {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Error revoking join access: {e}")
        return False

# ===================== 🔥 VERIFIED CHANNELS FUNCTIONS (NEW) =====================
def add_verified_channel(channel_id, channel_name):
    """Add a verified video channel"""
    try:
        channel_data = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'verified_at': datetime.utcnow(),
            'verified_by': ADMIN_ID,
            'is_active': True
        }
        verified_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': channel_data},
            upsert=True
        )
        logger.info(f"✅ Verified channel added: {channel_name} ({channel_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding verified channel: {e}")
        return False

def remove_verified_channel(channel_id):
    """Remove a verified video channel"""
    try:
        result = verified_channels_col.delete_one({'channel_id': channel_id})
        logger.info(f"✅ Verified channel removed: {channel_id}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing verified channel: {e}")
        return False

def get_verified_channels():
    """Get all verified video channels"""
    try:
        channels = list(verified_channels_col.find({'is_active': True}))
        return channels
    except Exception as e:
        logger.error(f"Error getting verified channels: {e}")
        return []

def is_channel_verified(channel_id):
    """Check if channel is verified for video notifications"""
    try:
        channel = verified_channels_col.find_one({'channel_id': channel_id, 'is_active': True})
        return channel is not None
    except Exception as e:
        logger.error(f"Error checking verified channel: {e}")
        return False

def get_verified_channel_stats():
    """Get verified channels count"""
    try:
        return verified_channels_col.count_documents({'is_active': True})
    except Exception as e:
        logger.error(f"Error getting verified channel stats: {e}")
        return 0

# ===================== 🔥 DIRECT UPLOAD FUNCTIONS =====================
def generate_unique_code(length=8):
    """Generate a unique alphanumeric code"""
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        # Check if code already exists
        if not direct_videos_col.find_one({'code': code}):
            return code

def save_direct_video(file_id, file_unique_id, title, media_type, code=None):
    """Save directly uploaded video to database"""
    try:
        if not code:
            code = generate_unique_code()
        
        video_data = {
            'code': code,
            'file_id': file_id,
            'file_unique_id': file_unique_id,
            'title': title,
            'media_type': media_type,
            'is_active': True,
            'views': 0,
            'created_at': datetime.utcnow()
        }
        direct_videos_col.insert_one(video_data)
        logger.info(f"✅ Direct video saved: code={code}, type={media_type}")
        return code
    except Exception as e:
        logger.error(f"Error saving direct video: {e}")
        return None

def get_direct_video(code):
    """Get direct video by code"""
    try:
        return direct_videos_col.find_one({'code': code, 'is_active': True})
    except Exception as e:
        logger.error(f"Error getting direct video: {e}")
        return None

def delete_direct_video(code):
    """Delete/deactivate direct video by code"""
    try:
        result = direct_videos_col.update_one(
            {'code': code},
            {'$set': {'is_active': False, 'deleted_at': datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error deleting direct video: {e}")
        return False

def increment_direct_video_view(code):
    """Increment view count for direct video"""
    try:
        direct_videos_col.update_one(
            {'code': code},
            {'$inc': {'views': 1}}
        )
    except Exception as e:
        logger.error(f"Error incrementing direct video view: {e}")

def get_all_direct_videos(limit=50):
    """Get all active direct videos"""
    try:
        return list(direct_videos_col.find(
            {'is_active': True},
            sort=[('created_at', -1)],
            limit=limit
        ))
    except Exception as e:
        logger.error(f"Error getting direct videos: {e}")
        return []

def get_all_channel_videos(limit=200):
    """Get all saved channel videos (from verified channels)"""
    try:
        return list(videos_col.find(
            {},
            sort=[('saved_at', -1)],
            limit=limit
        ))
    except Exception as e:
        logger.error(f"Error getting channel videos: {e}")
        return []

def get_video_not_found_keyboard():
    """Always returns a keyboard — mini app button দেখাবে কি না setting এ নির্ভর করে"""
    show_button = get_setting('video_not_found_button', True)
    if not show_button:
        return InlineKeyboardMarkup([[make_mini_app_button("🔄 Try Again")]])
    return InlineKeyboardMarkup([[make_mini_app_button("🎬 Open CINEFLIX App")]])


def get_mini_app_url(url_key):
    """Get Mini App URL for a specific location. Falls back to legacy mini_app_url if not set."""
    url = get_setting(url_key, '')
    if not url:
        url = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
    return url

def make_mini_app_button_from_url(text, url):
    """Build a button from a given URL — t.me/ → url button, others → web_app button."""
    if not url:
        return None
    if url.startswith('https://t.me/'):
        return InlineKeyboardButton(text, url=url)
    return InlineKeyboardButton(text, web_app={"url": url})

def make_mini_app_button(text="🎮 Open CINEFLIX App"):
    """
    Mini App URL type অনুযায়ী সঠিক button বানাবে।
    https://t.me/... → url button (direct Telegram link)
    https://... vercel/other → web_app button (opens inside Telegram as Mini App)
    """
    url = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
    if not url:
        url = DEFAULT_SETTINGS['mini_app_url']
    if url.startswith('https://t.me/'):
        return InlineKeyboardButton(text, url=url)
    return InlineKeyboardButton(text, web_app={"url": url})


# ===================== FORCE JOIN HELPERS =====================

def format_channels_list(channels, index_start=1):
    """Format channels as numbered list"""
    lines = []
    for i, channel in enumerate(channels, index_start):
        name = channel.get('name', 'Channel')
        lines.append(f"{i}. 🔒 **{name}**")
    return "\n".join(lines)


def build_force_join_keyboard(all_channels, not_joined_ids, video_id, is_direct=False):
    """
    সব channel একসাথে দেখাবে।
    ✅ = joined, 🔒 = not joined (clickable)
    সবশেষে সবসময় verify button থাকবে।
    Folder mode এ folder button + individual channels + verify button।
    """
    keyboard = []
    verify_cb = f"verify_direct_{video_id}" if is_direct else f"verify_{video_id}"

    folder_enabled = get_setting('folder_link_enabled', False)
    folder_url = get_setting('folder_link_url', '')

    if folder_enabled and folder_url and not_joined_ids:
        keyboard.append([InlineKeyboardButton("📁 Join All Channels (1-Click)", url=folder_url)])
        for i, ch in enumerate(all_channels):
            ch_id = ch['channel_id']
            name = ch.get('display_name') or ch.get('name') or f"Channel {i+1}"
            invite_link = ch.get('invite_link')
            username = ch.get('username', '')
            if ch_id not in not_joined_ids:
                keyboard.append([InlineKeyboardButton(f"\u2705  {name}", callback_data="noop_joined")])
            else:
                if invite_link:
                    keyboard.append([InlineKeyboardButton(f"\U0001f512  {name}", url=invite_link)])
                elif username:
                    keyboard.append([InlineKeyboardButton(f"\U0001f512  {name}", url=f"https://t.me/{username}")])
                else:
                    keyboard.append([InlineKeyboardButton(f"\U0001f512  {name}", callback_data="noop_locked")])
        keyboard.append([InlineKeyboardButton("\u2705 I Joined - Unlock Now", callback_data=verify_cb)])
        return InlineKeyboardMarkup(keyboard)

    # Normal mode
    for i, ch in enumerate(all_channels):
        ch_id = ch['channel_id']
        name = ch.get('display_name') or ch.get('name') or f"Channel {i+1}"
        invite_link = ch.get('invite_link')
        username = ch.get('username', '')

        if ch_id not in not_joined_ids:
            keyboard.append([InlineKeyboardButton(f"\u2705  {name}", callback_data="noop_joined")])
        else:
            if invite_link:
                url = invite_link
            elif username:
                url = f"https://t.me/{username}"
            else:
                keyboard.append([InlineKeyboardButton(f"\U0001f512  {name}", callback_data="noop_locked")])
                continue
            keyboard.append([InlineKeyboardButton(f"\U0001f512  {name}", url=url)])

    keyboard.append([InlineKeyboardButton("\u2705 I Joined - Unlock Now", callback_data=verify_cb)])
    return InlineKeyboardMarkup(keyboard)


def build_force_join_text(all_channels, not_joined_ids):
    """Professional clean lock message"""
    total = len(all_channels)
    remaining = len(not_joined_ids)
    done = total - remaining

    # Progress bar style
    filled = "▓" * done
    empty = "░" * remaining
    progress = f"{filled}{empty}"

    if done == 0:
        return (
            f"🎬 **Free Content Unlock করুন!**\n\n"
            f"নিচের **{total}টি channel** join করলেই পাবেন:\n"
            f"✨ Movies · Series · Anime · Exclusive\n\n"
            f"📊 Progress: {progress} `0/{total}`\n\n"
            f"👇 Channel join করুন — content আপনাআপনি unlock হয়ে যাবে!"
        )
    elif remaining == 1:
        return (
            f"🎬 **প্রায় হয়ে গেছে!**\n\n"
            f"📊 Progress: {progress} `{done}/{total}`\n\n"
            f"✅ {done}টি done! মাত্র **১টি channel** বাকি।\n\n"
            f"👇 শেষ channel join করুন — content unlock হয়ে যাবে!"
        )
    else:
        return (
            f"🎬 **Free Content Unlock করুন!**\n\n"
            f"📊 Progress: {progress} `{done}/{total}`\n\n"
            f"✅ {done}টি done — আরও **{remaining}টি** বাকি।\n\n"
            f"👇 বাকি channel গুলো join করুন — content আপনাআপনি unlock হবে!"
        )


async def check_channel_access(bot, user_id, channel):
    """
    Check if user has access to a channel.

    Logic:
    1. Telegram API তে member/admin/creator/restricted → access দাও
    2. left/kicked → no access
    3. Private channel: left/kicked কিন্তু DB তে pending request আছে → access দাও
       (bot approve করেছে কিন্তু Telegram এখনো reflect করেনি)
    4. Bot not admin in channel → skip (don't block user)
    """
    channel_id = channel['channel_id']

    # ── Telegram API check (সবসময়) ──
    try:
        member = await bot.get_chat_member(channel_id, user_id)

        if member.status in ['member', 'administrator', 'creator', 'restricted']:
            # Channel এ আছে → DB clean করো (পুরনো pending record থাকলে)
            try:
                pending_requests_col.delete_one({'user_id': user_id, 'channel_id': channel_id})
            except:
                pass
            return True

        elif member.status in ['left', 'kicked']:
            # User has LEFT the channel — always revoke access and return False.
            # Even for private channels: if Telegram says 'left', the user left.
            try:
                pending_requests_col.delete_one({'user_id': user_id, 'channel_id': channel_id})
            except:
                pass
            return False

        else:
            return False

    except BadRequest as e:
        err = str(e).lower()
        if 'chat not found' in err or 'bot is not a member' in err:
            logger.warning(f"⚠️ Bot not admin in channel {channel_id} — skipping check")
            return True
        logger.error(f"BadRequest checking channel {channel_id} for user {user_id}: {e}")
        return False
    except TelegramError as e:
        logger.error(f"TelegramError checking channel {channel_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking channel {channel_id}: {e}")
        return False


async def get_not_joined_ids(bot, user_id):
    """
    Returns list of channel_ids user hasn't accessed yet.
    Fast: DB check আগে, API call শুধু দরকার হলে।
    """
    all_channels = get_force_join_channels()
    not_joined = []

    for ch in all_channels:
        ch_id = ch['channel_id']
        has_access = await check_channel_access(bot, user_id, ch)
        if not has_access:
            not_joined.append(ch_id)

    return not_joined


# Legacy compatibility
async def get_channel_status_map(bot, user_id):
    """Legacy wrapper"""
    all_channels = get_force_join_channels()
    not_joined_ids = await get_not_joined_ids(bot, user_id)
    result = {}
    for ch in all_channels:
        cid = ch['channel_id']
        result[cid] = 'not_joined' if cid in not_joined_ids else 'member'
    return result


# ===================== EXISTING HELPERS CONTINUE =====================


def clear_join_request(user_id, channel_id):
    """Clear join request after user is approved"""
    try:
        pending_requests_col.update_one(
            {'user_id': user_id, 'channel_id': channel_id},
            {'$set': {'status': 'approved'}}
        )
        return True
    except Exception as e:
        logger.error(f"Error clearing join request: {e}")
        return False

def update_button(button_id, text=None, url=None):
    """Update button text or URL"""
    try:
        from bson.objectid import ObjectId
        update_data = {}
        if text:
            update_data['text'] = text
        if url:
            update_data['url'] = url
        
        if update_data:
            result = buttons_col.update_one(
                {'_id': ObjectId(button_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        return False
    except Exception as e:
        logger.error(f"Error updating button: {e}")
        return False

# ===================== ADVANCED AUTO CLEANUP SYSTEM =====================
async def cleanup_user_messages(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, keep_last: int = 0):
    """
    🔥 ADVANCED: Clean up all previous bot messages for ultra-clean chat
    keep_last: Number of recent messages to keep (0 = delete all)
    """
    cleanup_enabled = get_setting('message_cleanup_enabled', True)
    
    if not cleanup_enabled:
        return
    
    if user_id in user_all_messages:
        messages_to_delete = user_all_messages[user_id]
        
        # If keep_last > 0, only delete older messages
        if keep_last > 0 and len(messages_to_delete) > keep_last:
            messages_to_delete = messages_to_delete[:-keep_last]
        
        deleted_count = 0
        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted_count += 1
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")
        
        if deleted_count > 0:
            logger.info(f"🧹 Cleaned up {deleted_count} messages for user {user_id}")
        
        # Keep only last N messages if specified
        if keep_last > 0:
            user_all_messages[user_id] = user_all_messages[user_id][-keep_last:]
        else:
            user_all_messages[user_id] = []

async def track_message(user_id: int, message_id: int):
    """Track a message for future cleanup"""
    if user_id not in user_all_messages:
        user_all_messages[user_id] = []
    user_all_messages[user_id].append(message_id)
    
    # Auto-limit: Keep max 50 messages tracked (prevent memory bloat)


# 🔥 NEW: Enhanced send and cleanup helper
async def send_and_auto_cleanup(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    text: str,
    reply_markup=None,
    parse_mode=ParseMode.MARKDOWN,
    auto_delete_after: int = None
):
    """
    Smart send: Cleanup previous messages then send new one
    
    auto_delete_after: Seconds to auto-delete this message (None = keep)
    """
    # Cleanup previous messages first
    await cleanup_user_messages(context, user_id, chat_id)
    
    # Send new message
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    
    # Track for future cleanup
    await track_message(user_id, msg.message_id)
    
    # Schedule auto-delete if specified
    if auto_delete_after:
        context.job_queue.run_once(
            auto_delete_message,
            when=auto_delete_after,
            data={'chat_id': chat_id, 'message_id': msg.message_id, 'user_id': user_id}
        )
    
    return msg


async def auto_delete_message(context: ContextTypes.DEFAULT_TYPE):
    """Auto-delete a message after delay"""
    data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=data['chat_id'],
            message_id=data['message_id']
        )
        # Remove from tracking
        user_id = data['user_id']
        if user_id in user_all_messages:
            try:
                user_all_messages[user_id].remove(data['message_id'])
            except:
                pass
        logger.debug(f"⏰ Auto-deleted message {data['message_id']}")
    except Exception as e:
        logger.debug(f"Could not auto-delete message: {e}")


# 🔥 NEW: Edit message instead of sending new (cleaner!)
async def edit_or_send(
    query_or_context,
    text: str,
    reply_markup=None,
    parse_mode=ParseMode.MARKDOWN,
    is_query: bool = True
):
    """
    Try to edit existing message, fallback to new message
    
    is_query: True if query_or_context is CallbackQuery, False if Context
    """
    try:
        if is_query:
            # Edit via query
            await query_or_context.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            # Send new (can't edit)
            context = query_or_context
            msg = await context.bot.send_message(
                chat_id=context._chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return msg
    except Exception as e:
        logger.debug(f"Could not edit message, sending new: {e}")
        # Fallback: send new
        if is_query:
            msg = await query_or_context.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return msg
    if len(user_all_messages[user_id]) > 50:
        user_all_messages[user_id] = user_all_messages[user_id][-50:]

# ===================== ADMIN PANEL KEYBOARDS =====================

def admin_main_keyboard():
    """Main admin panel keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📺 Force Join Channels", callback_data="admin_channels"),
            InlineKeyboardButton("✅ Verified Video Channels", callback_data="admin_verified")
        ],
        [
            InlineKeyboardButton("🎬 My Uploaded Videos", callback_data="admin_video_list"),
            InlineKeyboardButton("📋 File IDs List", callback_data="admin_file_ids"),
        ],
        [
            InlineKeyboardButton("📤 Forward Channel Setup", callback_data="admin_forward_channel"),
        ],
        [
            InlineKeyboardButton("📝 Edit Messages", callback_data="admin_messages"),
            InlineKeyboardButton("🔘 Button Manager", callback_data="admin_buttons")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
        ],
        [
            InlineKeyboardButton("🎙️ Voice Manager", callback_data="admin_voice_manager")
        ],
        [
            InlineKeyboardButton("📢 Post Manager", callback_data="admin_post_manager"),
            InlineKeyboardButton("📌 Pinned Button", callback_data="admin_pinned_btn")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def channel_manager_keyboard():
    """Channel manager keyboard"""
    channels = get_force_join_channels()
    keyboard = []
    
    for i, ch in enumerate(channels):
        display_name = ch.get('display_name') or ch.get('name') or f"Channel {i+1}"
        channel_icon = "🔒" if ch.get('invite_link') else "📢"
        keyboard.append([
            InlineKeyboardButton(
                f"{channel_icon} {display_name}", 
                callback_data=f"view_channel_{ch['channel_id']}"
            ),
            InlineKeyboardButton(
                "✏️ Rename", 
                callback_data=f"rename_channel_{ch['channel_id']}"
            ),
            InlineKeyboardButton(
                "❌", 
                callback_data=f"remove_channel_{ch['channel_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add New Channel", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    
    return InlineKeyboardMarkup(keyboard)

def verified_channels_keyboard():
    """Verified video channels keyboard - 🔥 NEW"""
    channels = get_verified_channels()
    keyboard = []
    
    if channels:
        for ch in channels:
            channel_name = ch.get('channel_name', 'Unknown')
            channel_id = ch['channel_id']
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {channel_name}", 
                    callback_data=f"view_verified_{channel_id}"
                ),
                InlineKeyboardButton(
                    "❌ Remove", 
                    callback_data=f"remove_verified_{channel_id}"
                )
            ])
    else:
        keyboard.append([InlineKeyboardButton("📝 No verified channels yet", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton("➕ Add Verified Channel", callback_data="add_verified")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    
    return InlineKeyboardMarkup(keyboard)

def message_editor_keyboard():
    """Message editor keyboard"""
    keyboard = [
        [InlineKeyboardButton("✏️ Welcome Message", callback_data="edit_msg_welcome")],
        [InlineKeyboardButton("✏️ Help Message", callback_data="edit_msg_help")],
        [InlineKeyboardButton("✏️ Force Join Message", callback_data="edit_msg_force_join")],
        [InlineKeyboardButton("✏️ After Video Message", callback_data="edit_msg_after_video")],
        [InlineKeyboardButton("✏️ Video Not Found Message", callback_data="edit_msg_video_not_found")],
        [InlineKeyboardButton("✏️ Auto Reply Message", callback_data="edit_msg_auto_reply")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard():
    """Settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App URL", callback_data="setting_mini_app")],
        [InlineKeyboardButton("📢 Main Channel", callback_data="setting_main_channel")],
        [InlineKeyboardButton("🔒 Video Protection", callback_data="setting_protection")],
        [InlineKeyboardButton("🤖 Bot Name", callback_data="setting_bot_name")],
        [InlineKeyboardButton("💬 Auto Reply", callback_data="setting_auto_reply")],
        [InlineKeyboardButton("🧹 Message Cleanup", callback_data="setting_cleanup")],
        [InlineKeyboardButton("🎬 Welcome Media", callback_data="setting_welcome_media")],
        [InlineKeyboardButton("🎙️ Welcome Voice", callback_data="setting_welcome_voice")],
        [InlineKeyboardButton("📁 Folder Join Link", callback_data="setting_folder_link")],
        [InlineKeyboardButton("❌ Video Not Found Button", callback_data="setting_notfound_btn")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def button_manager_keyboard():
    """Button manager keyboard"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Welcome Button", callback_data="add_btn_welcome")],
        [InlineKeyboardButton("➕ Add After Video Button", callback_data="add_btn_after_video")],
        [InlineKeyboardButton("📋 View Welcome Buttons", callback_data="view_btn_welcome")],
        [InlineKeyboardButton("📋 View After Video Buttons", callback_data="view_btn_after_video")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===================== FORCE JOIN SYSTEM =====================

async def show_force_join(user_id, video_id, user_name, context, is_direct=False):
    """
    Professional step force join screen.
    সব channel একসাথে দেখাবে — যেকোনো order এ join করা যাবে।
    Pending request = access granted (admin approve লাগবে না)।
    """
    all_channels = get_force_join_channels()

    if not all_channels:
        # কোনো force join নেই — সরাসরি video দাও
        if is_direct:
            await send_direct_video_by_code(user_id, video_id, context)
        else:
            await send_video_direct_by_id(user_id, video_id, context)
        return

    not_joined_ids = await get_not_joined_ids(context.bot, user_id)

    if not not_joined_ids:
        # সব joined/pending — video দাও
        if is_direct:
            await send_direct_video_by_code(user_id, video_id, context)
        else:
            await send_video_direct_by_id(user_id, video_id, context)
        return

    text = build_force_join_text(all_channels, not_joined_ids)
    keyboard = build_force_join_keyboard(all_channels, not_joined_ids, video_id, is_direct)

    sent_msg = await context.bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await track_message(user_id, sent_msg.message_id)

    # Save for auto-update when join request arrives
    context.user_data[f"fj_video_{user_id}"] = video_id
    context.user_data[f"fj_msg_{user_id}"] = sent_msg.message_id
    context.user_data[f"fj_direct_{user_id}"] = is_direct

    logger.info(f"🔒 Force join shown: {len(not_joined_ids)}/{len(all_channels)} remaining for user {user_id}")


async def update_force_join_progress(user_id, context):
    """
    Private channel এ join request পাঠালে auto-update।
    Called by handle_chat_join_request।
    """
    video_id = context.user_data.get(f"fj_video_{user_id}")
    message_id = context.user_data.get(f"fj_msg_{user_id}")
    is_direct = context.user_data.get(f"fj_direct_{user_id}", False)

    if not video_id or not message_id:
        return

    all_channels = get_force_join_channels()
    not_joined_ids = await get_not_joined_ids(context.bot, user_id)

    if not not_joined_ids:
        # 🎉 সব done — video পাঠাও
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=message_id)
        except:
            pass

        context.user_data.pop(f"fj_video_{user_id}", None)
        context.user_data.pop(f"fj_msg_{user_id}", None)
        context.user_data.pop(f"fj_direct_{user_id}", None)

        if is_direct:
            await send_direct_video_by_code(user_id, video_id, context)
        else:
            await send_video_direct_by_id(user_id, video_id, context)

        logger.info(f"✅ Auto-unlocked video for user {user_id}")
    else:
        # Update message — progress দেখাও
        text = build_force_join_text(all_channels, not_joined_ids)
        keyboard = build_force_join_keyboard(all_channels, not_joined_ids, video_id, is_direct)
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.debug(f"Could not update force join message: {e}")


async def send_direct_video_by_code(user_id, code, context):
    """Send direct upload video by code after all channels joined"""
    video = get_direct_video(code)
    if not video:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        protect = get_setting('video_protection', True)
        media_type = video.get('media_type', 'video')
        file_id = video['file_id']
        
        if media_type == 'video':
            video_msg = await context.bot.send_video(chat_id=user_id, video=file_id, protect_content=protect)
        elif media_type == 'document':
            video_msg = await context.bot.send_document(chat_id=user_id, document=file_id, protect_content=protect)
        elif media_type == 'animation':
            video_msg = await context.bot.send_animation(chat_id=user_id, animation=file_id, protect_content=protect)
        else:
            video_msg = await context.bot.send_video(chat_id=user_id, video=file_id, protect_content=protect)
        
        increment_direct_video_view(code)
        
        after_buttons = get_buttons('after_video')
        if after_buttons:
            keyboard = []
            for btn in after_buttons:
                if btn['type'] == 'web_app':
                    keyboard.append([InlineKeyboardButton(btn['text'], web_app={"url": btn['url']})])
                else:
                    keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        else:
            keyboard = [[make_mini_app_button("🔙 Back to App")]]
        
        after_msg = await context.bot.send_message(
            chat_id=user_id,
            text=get_message('after_video'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await track_message(user_id, video_msg.message_id)
        await track_message(user_id, after_msg.message_id)
        logger.info(f"✅ Direct video {code} sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending direct video by code: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )


async def send_video_direct_by_id(user_id, video_id, context):
    """Send video directly by ID without force join check"""
    # Convert video_id to message_id
    try:
        message_id = int(video_id)
    except ValueError:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    video = get_video(message_id)
    
    if not video:
        await context.bot.send_message(
            chat_id=user_id,
            text=get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Send video using copy_message (same as manual verify flow)
    try:
        protect = get_setting('video_protection', True)
        
        video_msg = await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=video['channel_id'],
            message_id=message_id,
            protect_content=protect
        )
        
        increment_video_view(message_id)
        
        # After video message with dynamic buttons
        after_buttons = get_buttons('after_video')
        
        if after_buttons:
            # Use custom buttons from database
            keyboard = []
            for btn in after_buttons:
                if btn['type'] == 'web_app':
                    keyboard.append([InlineKeyboardButton(btn['text'], web_app={"url": btn['url']})])
                else:  # url type
                    keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        else:
            # Default button
            keyboard = [[make_mini_app_button("🔙 Back to App")]]
        
        after_msg = await context.bot.send_message(
            chat_id=user_id,
            text=get_message('after_video'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Track for future cleanup
        await track_message(user_id, video_msg.message_id)
        await track_message(user_id, after_msg.message_id)
        
        logger.info(f"✅ Video {message_id} sent to user {user_id}")
        
    except BadRequest as e:
        if "message to copy not found" in str(e).lower():
            await context.bot.send_message(
                chat_id=user_id,
                text=get_message('video_not_found'),
                reply_markup=get_video_not_found_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            logger.error(f"Error sending video: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Error sending video. Please try again.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Error in send_video_direct_by_id: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Error sending video. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )

# ===================== CHAT JOIN REQUEST HANDLER =====================
async def _clear_pending_after_delay(user_id: int, channel_id: int, delay: int = 10):
    """
    Approve করার পরে কিছুক্ষণ অপেক্ষা করে DB record মুছে দাও।
    তাহলে পরেরবার শুধু Telegram API check হবে।
    User বের হয়ে গেলে আর DB এর কারণে access পাবে না।
    """
    await asyncio.sleep(delay)
    try:
        pending_requests_col.delete_one({'user_id': user_id, 'channel_id': channel_id})
        logger.debug(f"🧹 Cleared pending record: user {user_id} → channel {channel_id}")
    except Exception as e:
        logger.error(f"Error clearing pending record: {e}")


async def handle_chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🔥 AUTO-APPROVE: Private channel এ join request আসলে bot নিজেই approve করবে।
    - "Link expired" সমস্যা আর হবে না
    - Admin কে manually approve করতে হবে না
    - Approved হলেই DB তে mark হবে, user unlock পাবে
    - 10 সেকেন্ড পরে DB record মুছে যাবে — পরেরবার Telegram API check হবে
    """
    chat_join_request = update.chat_join_request
    user = chat_join_request.from_user
    chat = chat_join_request.chat

    logger.info(f"🔔 JOIN REQUEST: User {user.id} (@{user.username}) → Channel {chat.id} ({chat.title})")

    approved = False

    # Step 1: Bot নিজে approve করবে
    try:
        await context.bot.approve_chat_join_request(
            chat_id=chat.id,
            user_id=user.id
        )
        # DB তে approved mark করো — শুধু unlock এর জন্য (10s পরে মুছে যাবে)
        mark_join_approved(user.id, chat.id)
        approved = True
        logger.info(f"✅ AUTO-APPROVED: User {user.id} → Channel {chat.id}")
    except Exception as e:
        error_msg = str(e).lower()
        if "user_already_participant" in error_msg or "hide_requester_missing" in error_msg:
            mark_join_approved(user.id, chat.id)
            approved = True
            logger.info(f"✅ Already member, marked approved: User {user.id}")
        elif "not enough rights" in error_msg:
            mark_join_request_sent(user.id, chat.id)
            approved = True  # pending হিসেবে রাখো — unlock হবে
            logger.warning(f"⚠️ Bot cannot approve in channel {chat.id} — marked pending.")
        else:
            mark_join_request_sent(user.id, chat.id)
            approved = True
            logger.error(f"❌ Could not approve user {user.id} in {chat.id}: {e}")

    # Step 2: Force join message auto-update করো
    await update_force_join_progress(user.id, context)

    # Step 3: 10 সেকেন্ড পরে DB record মুছে দাও
    # তাহলে পরেরবার user বের হলে আবার join করতে হবে
    if approved:
        asyncio.create_task(_clear_pending_after_delay(user.id, chat.id, delay=10))

# ===================== START COMMAND =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with ultra-clean chat experience"""
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)
    
    # 🔥 ADVANCED: Track user's /start command message for deletion
    user_command_msg_id = update.message.message_id
    
    # 🧹 STEP 1: Cleanup ALL old messages (ultra-clean)
    await cleanup_user_messages(context, user.id, update.effective_chat.id)
    
    # Check for video deep link
    if context.args and len(context.args) > 0:
        video_id = context.args[0]
        
        # 🔥 Delete user's command message for clean chat
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=user_command_msg_id
            )
        except:
            pass
        
        # 🔥 Check if it's a direct upload code (letters+numbers) or channel message_id (numbers only)
        if video_id.isdigit():
            # Old system: channel video by message_id
            await handle_video_request(update, context, video_id)
        else:
            # New system: direct upload by unique code
            await handle_direct_video_request(update, context, video_id)
        return
    
    # Get settings
    mini_app_url = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
    
    # Build keyboard with custom buttons
    keyboard = []
    
    # Get custom welcome buttons from database
    custom_buttons = get_buttons('welcome')
    
    if custom_buttons:
        # Use custom buttons from database
        for btn in custom_buttons:
            if btn['type'] == 'web_app':
                keyboard.append([InlineKeyboardButton(btn['text'], web_app={"url": btn['url']})])
            else:  # url type
                keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
    else:
        # Default buttons if no custom buttons set
        main_channel = get_setting('main_channel_username', DEFAULT_SETTINGS['main_channel_username'])
        # শুধু App button — welcome text এর সাথে
        if mini_app_url.startswith('https://t.me/'):
            app_button = InlineKeyboardButton("🎮 Open CINEFLIX App", url=mini_app_url)
        else:
            app_button = InlineKeyboardButton("🎮 Open CINEFLIX App", web_app={"url": mini_app_url})
        keyboard = [
            [app_button],
        ]
    
    welcome_text = get_message('welcome').format(name=user.first_name)
    
    try:
        # ① 🎬 Send welcome media FIRST (if enabled) — চোখে পড়বে আগে
        welcome_media_enabled = get_setting('welcome_media_enabled', False)
        
        if welcome_media_enabled:
            media_file_id = get_setting('welcome_media_file_id')
            media_type = get_setting('welcome_media_type')
            
            if media_file_id and media_type:
                try:
                    media_msg = None
                    if media_type == 'photo':
                        media_msg = await update.message.reply_photo(photo=media_file_id)
                    elif media_type == 'animation':
                        media_msg = await update.message.reply_animation(animation=media_file_id)
                    elif media_type == 'video':
                        media_msg = await update.message.reply_video(video=media_file_id)
                    
                    if media_msg:
                        await track_message(user.id, media_msg.message_id)
                        logger.info(f"✅ Welcome media sent to user {user.id}")
                except Exception as e:
                    logger.error(f"Error sending welcome media: {e}")
        
        # ② 📝 Send welcome text + App button only
        sent_msg = await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await track_message(user.id, sent_msg.message_id)
        
        # ③ 🎙️ Send welcome voice MIDDLE
        welcome_voice_enabled = get_setting('welcome_voice_enabled', False)
        if welcome_voice_enabled:
            voice_file_id = get_setting('welcome_voice_file_id')
            if voice_file_id:
                try:
                    voice_msg = await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=voice_file_id
                    )
                    await track_message(user.id, voice_msg.message_id)
                    logger.info(f"✅ Welcome voice sent to user {user.id}")
                except Exception as e:
                    logger.error(f"Error sending welcome voice: {e}")
        
        # ④ 📢 Join Channel + ❓ Help — সবার নিচে
        if not custom_buttons:
            main_channel = get_setting('main_channel_username', DEFAULT_SETTINGS['main_channel_username'])
            bottom_keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{main_channel}")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ]
            bottom_msg = await update.message.reply_text(
                "👇",
                reply_markup=InlineKeyboardMarkup(bottom_keyboard)
            )
            await track_message(user.id, bottom_msg.message_id)
        
        # 🔥 DELETE user's /start command for ultra-clean chat
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=user_command_msg_id
            )
            logger.debug(f"🧹 Deleted user's /start command")
        except Exception as e:
            logger.debug(f"Could not delete user command: {e}")
        
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

# ===================== 🔥 DIRECT VIDEO REQUEST HANDLER =====================
async def handle_direct_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """Handle direct upload video request by unique code"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Cleanup old messages
    await cleanup_user_messages(context, user.id, chat_id)
    
    # Get video from direct_videos collection
    video = get_direct_video(code)
    
    if not video:
        msg = await update.message.reply_text(
            get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        await track_message(user.id, msg.message_id)
        return
    # Check if any channel not joined
    not_joined_ids = await get_not_joined_ids(context.bot, user.id)
    
    if not_joined_ids:
        await show_force_join(
            user_id=user.id,
            video_id=code,
            user_name=user.first_name or "User",
            context=context,
            is_direct=True
        )
        return
    
    # Send video directly
    try:
        protect = get_setting('video_protection', True)
        media_type = video.get('media_type', 'video')
        file_id = video['file_id']
        
        if media_type == 'video':
            video_msg = await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                protect_content=protect
            )
        elif media_type == 'document':
            video_msg = await context.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                protect_content=protect
            )
        elif media_type == 'animation':
            video_msg = await context.bot.send_animation(
                chat_id=chat_id,
                animation=file_id,
                protect_content=protect
            )
        else:
            video_msg = await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                protect_content=protect
            )
        
        increment_direct_video_view(code)
        
        # After video message
        after_buttons = get_buttons('after_video')
        if after_buttons:
            keyboard = []
            for btn in after_buttons:
                if btn['type'] == 'web_app':
                    keyboard.append([InlineKeyboardButton(btn['text'], web_app={"url": btn['url']})])
                else:
                    keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        else:
            keyboard = [[make_mini_app_button("🔙 Back to App")]]
        
        after_msg = await update.message.reply_text(
            get_message('after_video'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await track_message(user.id, video_msg.message_id)
        await track_message(user.id, after_msg.message_id)
        logger.info(f"✅ Direct video {code} sent to user {user.id}")
        
    except Exception as e:
        logger.error(f"Error sending direct video: {e}")
        await update.message.reply_text(
            get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

# ===================== VIDEO REQUEST HANDLER =====================
async def handle_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: str):
    """Handle video playback request"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # NEW: Cleanup old messages first (for clean experience)
    await cleanup_user_messages(context, user.id, chat_id)
    
    try:
        message_id = int(video_id)
    except ValueError:
        msg = await update.message.reply_text(
            get_message('video_not_found'),
            reply_markup=get_video_not_found_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        await track_message(user.id, msg.message_id)
        return
    
    # Get video from database
    video = get_video(message_id)
    if not video:
        keyboard = [[make_mini_app_button("🎬 Open CINEFLIX App")]]
        msg = await update.message.reply_text(
            get_message('video_not_found'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await track_message(user.id, msg.message_id)
        return
    
    # Check force join channels — সবসময় Telegram API check
    not_joined_ids = await get_not_joined_ids(context.bot, user.id)
    force_channels = get_force_join_channels()
    not_joined = [ch for ch in force_channels if ch['channel_id'] in not_joined_ids]

    if not_joined:
        # 🔥 UPGRADED: Use step-by-step show_force_join
        await show_force_join(
            user_id=user.id,
            video_id=video_id,
            user_name=user.first_name or "User",
            context=context,
            is_direct=False
        )
        return
    
    # User joined all channels - send video
    try:
        protect = get_setting('video_protection', True)
        
        video_msg = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=video['channel_id'],
            message_id=message_id,
            protect_content=protect
        )
        
        increment_video_view(message_id)
        
        # After video message with dynamic buttons
        after_buttons = get_buttons('after_video')
        
        if after_buttons:
            # Use custom buttons from database
            keyboard = []
            for btn in after_buttons:
                if btn['type'] == 'web_app':
                    keyboard.append([InlineKeyboardButton(btn['text'], web_app={"url": btn['url']})])
                else:  # url type
                    keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        else:
            # Default button
            keyboard = [[make_mini_app_button("🔙 Back to App")]]
        
        after_msg = await update.message.reply_text(
            get_message('after_video'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Track these messages for cleanup
        await track_message(user.id, video_msg.message_id)
        await track_message(user.id, after_msg.message_id)
        
        logger.info(f"✅ Video {message_id} sent to user {user.id}")
        
    except BadRequest as e:
        if "message to copy not found" in str(e).lower():
            msg = await update.message.reply_text(
                get_message('video_not_found'),
                reply_markup=get_video_not_found_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            await track_message(user.id, msg.message_id)
        else:
            logger.error(f"Error sending video: {e}")

# ===================== CALLBACK QUERY HANDLER =====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Help button
    if data == "help":
        await query.message.reply_text(
            get_message('help'),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ── noop buttons (separator, joined indicator) ──
    if data in ("noop_sep", "noop_joined", "noop_locked"):
        if data == "noop_joined":
            await query.answer("✅ এই channel টি join করা হয়েছে।")
        else:
            await query.answer()
        return

    # ── Verify 🔐 button (both direct and channel videos) ──
    if data.startswith("verify_direct_") or data.startswith("verify_"):
        user = query.from_user

        if data.startswith("verify_direct_"):
            video_id = data.replace("verify_direct_", "")
            is_direct = True
        else:
            video_id = data.replace("verify_", "")
            is_direct = False
            # Validate channel video exists
            try:
                mid = int(video_id)
            except ValueError:
                await query.answer("❌ ভিডিও পাওয়া যাচ্ছে না।", show_alert=True)
                return
            if not get_video(mid):
                await query.answer("❌ ভিডিও পাওয়া যাচ্ছে না।", show_alert=True)
                return

        # Real-time check
        all_channels = get_force_join_channels()
        not_joined_ids = await get_not_joined_ids(context.bot, user.id)

        if not_joined_ids:
            # এখনো সব join হয়নি — alert + message update
            remaining = len(not_joined_ids)
            done = len(all_channels) - remaining
            if done == 0:
                alert_text = f"⚠️ এখনো কোনো channel join করা হয়নি!\nChannel গুলোতে join করে আবার Verify চাপুন।"
            else:
                alert_text = f"⚠️ এখনো {remaining}টি channel বাকি!\nবাকি channel গুলো join করে আবার Verify চাপুন।"
            await query.answer(alert_text, show_alert=True)
            # Update message to show latest state
            text = build_force_join_text(all_channels, not_joined_ids)
            keyboard = build_force_join_keyboard(all_channels, not_joined_ids, video_id, is_direct)
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
            return

        # ✅ সব joined/pending — video দাও
        try:
            await query.message.delete()
        except:
            pass

        if is_direct:
            await send_direct_video_by_code(user.id, video_id, context)
        else:
            await send_video_direct_by_id(user.id, video_id, context)
        return

    # Admin panel navigation
    if data == "admin_main":
        stats = get_stats()
        text = f"""🔧 **CINEFLIX ADMIN PANEL**

📊 **Statistics:**
👥 Total Users: {stats['users']}
🔥 Active Today: {stats['active_today']}
📹 Videos: {stats['videos']}
👁️ Top Views: {stats['top_views']}
🔒 Force Join: {stats['force_join']}

Select an option below:"""
        
        await query.edit_message_text(
            text,
            reply_markup=admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_video_list" or data.startswith("admin_video_list_page_"):
        # 🔥 Show uploaded videos list with pagination
        page = 0
        if data.startswith("admin_video_list_page_"):
            page = int(data.replace("admin_video_list_page_", ""))
        
        per_page = 8
        all_videos = get_all_direct_videos(limit=200)
        total = len(all_videos)
        start = page * per_page
        end = start + per_page
        page_videos = all_videos[start:end]
        
        if not page_videos:
            await query.edit_message_text(
                "🎬 **My Uploaded Videos**\n\n📭 কোনো video upload করা নেই।\n\nBot এ video পাঠালে এখানে দেখাবে।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_main")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"🎬 **Uploaded Videos** ({total} total)\n\n"
        keyboard = []
        
        for v in page_videos:
            code = v['code']
            title = v.get('title', 'Untitled')[:25]
            views = v.get('views', 0)
            media_type = v.get('media_type', 'video')
            icon = "🎬" if media_type == 'video' else "📄" if media_type == 'document' else "🎞️"
            
            text += f"{icon} `{code}` — {title} ({views} views)\n"
            keyboard.append([
                InlineKeyboardButton(f"🗑️ Delete {code}", callback_data=f"del_direct_{code}"),
                InlineKeyboardButton(f"🔗 Copy", callback_data=f"copy_direct_{code}")
            ])
        
        # Pagination buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_video_list_page_{page-1}"))
        if end < total:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_video_list_page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("del_direct_"):
        code = data.replace("del_direct_", "")
        if delete_direct_video(code):
            await query.answer(f"✅ Video {code} deleted!")
            # Refresh list
            fake_data = query.data
            query.data = "admin_video_list"
            await button_callback(update, context)
            query.data = fake_data
        else:
            await query.answer("❌ Failed to delete", show_alert=True)
    
    elif data.startswith("copy_direct_"):
        code = data.replace("copy_direct_", "")
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={code}"
        await query.answer(f"Link: {link}", show_alert=True)
    
    # ============================================================
    # 🔥 FILE IDs LIST — Verified Channel saved videos (Admin only)
    # ============================================================
    elif data == "admin_file_ids" or data.startswith("admin_file_ids_page_"):
        if user_id != ADMIN_ID:
            return
        
        page = 0
        if data.startswith("admin_file_ids_page_"):
            page = int(data.replace("admin_file_ids_page_", ""))
        
        per_page = 8
        all_videos = get_all_channel_videos(limit=500)
        total = len(all_videos)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_videos = all_videos[start_idx:end_idx]
        
        if not page_videos:
            await query.edit_message_text(
                "📋 **Channel Video File IDs**\n\n"
                "📭 এখনো কোনো verified channel এ video upload হয়নি।\n\n"
                "Verified channel এ video upload করলে এখানে দেখাবে।",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="admin_main")
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        bot_info = await context.bot.get_me()
        text = f"📋 **Channel Video File IDs** (মোট {total}টি) — পাতা {page+1}\n\n"
        text += "Verified channel থেকে save হওয়া video গুলোর File ID:\n\n"
        keyboard = []
        
        for v in page_videos:
            msg_id = v['message_id']
            ch_name = v.get('channel_name', 'Unknown')[:15]
            media_type = v.get('media_type', 'video')
            views = v.get('views', 0)
            icon = "🎬" if media_type == 'video' else "📸" if media_type == 'photo' else "📄" if media_type == 'document' else "🎞️"
            
            text += f"{icon} `{msg_id}` | {ch_name} | 👁 {views}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 Copy ID: {msg_id}",
                    callback_data=f"fileid_copy_ch_{msg_id}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_file_ids_page_{page-1}"))
        if end_idx < total:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_file_ids_page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("fileid_copy_ch_"):
        if user_id != ADMIN_ID:
            return
        msg_id = data.replace("fileid_copy_ch_", "")
        bot_info = await context.bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={msg_id}"
        await query.answer("✅ নিচে ID ও Deep Link পাঠানো হয়েছে!")
        # Send as separate copyable messages
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"📋 <b>Channel Video File ID:</b>\n\n"
                 f"🔑 File ID:\n<code>{msg_id}</code>\n\n"
                 f"🌐 Deep Link:\n{deep_link}\n\n"
                 f"👇 <b>নিচের code টা tap করে copy করুন:</b>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"<code>{msg_id}</code>",
            parse_mode=ParseMode.HTML
        )
    
    # ============================================================
    # 🔥 NEW: FORWARD CHANNEL SETUP - Admin only
    # ============================================================
    # ============================================================
    # 🔥 UNLIMITED FORWARD CHANNELS - Admin only
    # ============================================================
    elif data == "admin_forward_channel":
        if user_id != ADMIN_ID:
            return
        
        fwd_channels = get_forward_channels()
        count = len(fwd_channels)
        active_count = sum(1 for c in fwd_channels if c.get('enabled', True))
        
        text = f"📤 **Forward Channels** (মোট {count}টি | চালু {active_count}টি)\n\n"
        text += "Bot এ যা upload হবে সব চালু channel গুলোতে forward হবে।\n"
        text += "Bot ban হলেও channel থেকে video দেখা যাবে।\n\n━━━━━━━━━━━━━━\n"
        keyboard = []
        
        if fwd_channels:
            for ch in fwd_channels:
                ch_name = ch.get('channel_name', 'Unknown')
                ch_id = ch['channel_id']
                enabled = ch.get('enabled', True)
                status_icon = "✅" if enabled else "❌"
                toggle_label = "⏸ OFF করুন" if enabled else "▶️ ON করুন"
                text += f"{status_icon} **{ch_name}**\n   ID: `{ch_id}`\n\n"
                keyboard.append([
                    InlineKeyboardButton(toggle_label, callback_data=f"fwd_toggle_{ch_id}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"fwd_remove_{ch_id}")
                ])
        else:
            text += "📭 এখনো কোনো channel add করা হয়নি।\n\n"
        
        text += "━━━━━━━━━━━━━━\nনতুন channel add করতে নিচের বাটন চাপুন:"
        keyboard.append([InlineKeyboardButton("➕ নতুন Channel Add করুন", callback_data="fwd_add_channel")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("fwd_toggle_"):
        if user_id != ADMIN_ID:
            return
        ch_id = int(data.replace("fwd_toggle_", ""))
        new_state = toggle_forward_channel(ch_id)
        if new_state is True:
            await query.answer("✅ Forward চালু হয়েছে!")
        elif new_state is False:
            await query.answer("⏸ Forward বন্ধ করা হয়েছে!")
        else:
            await query.answer("❌ Error!", show_alert=True)
        
        fwd_channels = get_forward_channels()
        count = len(fwd_channels)
        active_count = sum(1 for c in fwd_channels if c.get('enabled', True))
        text = f"📤 **Forward Channels** (মোট {count}টি | চালু {active_count}টি)\n\nBot এ যা upload হবে সব চালু channel গুলোতে forward হবে।\nBot ban হলেও channel থেকে video দেখা যাবে।\n\n━━━━━━━━━━━━━━\n"
        keyboard = []
        if fwd_channels:
            for ch in fwd_channels:
                ch_name = ch.get('channel_name', 'Unknown')
                ch_id2 = ch['channel_id']
                enabled = ch.get('enabled', True)
                status_icon = "✅" if enabled else "❌"
                toggle_label = "⏸ OFF করুন" if enabled else "▶️ ON করুন"
                text += f"{status_icon} **{ch_name}**\n   ID: `{ch_id2}`\n\n"
                keyboard.append([
                    InlineKeyboardButton(toggle_label, callback_data=f"fwd_toggle_{ch_id2}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"fwd_remove_{ch_id2}")
                ])
        else:
            text += "📭 এখনো কোনো channel add করা হয়নি।\n\n"
        text += "━━━━━━━━━━━━━━\nনতুন channel add করতে নিচের বাটন চাপুন:"
        keyboard.append([InlineKeyboardButton("➕ নতুন Channel Add করুন", callback_data="fwd_add_channel")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    elif data.startswith("fwd_remove_"):
        if user_id != ADMIN_ID:
            return
        ch_id = int(data.replace("fwd_remove_", ""))
        if remove_forward_channel(ch_id):
            await query.answer("✅ Channel remove করা হয়েছে!")
        else:
            await query.answer("❌ Remove করা যায়নি!", show_alert=True)
        
        fwd_channels = get_forward_channels()
        count = len(fwd_channels)
        active_count = sum(1 for c in fwd_channels if c.get('enabled', True))
        text = f"📤 **Forward Channels** (মোট {count}টি | চালু {active_count}টি)\n\nBot এ যা upload হবে সব চালু channel গুলোতে forward হবে।\nBot ban হলেও channel থেকে video দেখা যাবে।\n\n━━━━━━━━━━━━━━\n"
        keyboard = []
        if fwd_channels:
            for ch in fwd_channels:
                ch_name = ch.get('channel_name', 'Unknown')
                ch_id2 = ch['channel_id']
                enabled = ch.get('enabled', True)
                status_icon = "✅" if enabled else "❌"
                toggle_label = "⏸ OFF করুন" if enabled else "▶️ ON করুন"
                text += f"{status_icon} **{ch_name}**\n   ID: `{ch_id2}`\n\n"
                keyboard.append([
                    InlineKeyboardButton(toggle_label, callback_data=f"fwd_toggle_{ch_id2}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"fwd_remove_{ch_id2}")
                ])
        else:
            text += "📭 এখনো কোনো channel add করা হয়নি।\n\n"
        text += "━━━━━━━━━━━━━━\nনতুন channel add করতে নিচের বাটন চাপুন:"
        keyboard.append([InlineKeyboardButton("➕ নতুন Channel Add করুন", callback_data="fwd_add_channel")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    elif data == "fwd_add_channel":
        if user_id != ADMIN_ID:
            return
        admin_states[user_id] = {'action': 'add_forward_channel'}
        await query.message.reply_text(
            "📤 **Forward Channel Add করুন**\n\n"
            "যে channel এ video forward হবে সেই channel এর **ID** পাঠান।\n"
            "একাধিক channel add করতে পারবেন — যতবার খুশি এই step repeat করুন।\n\n"
            "**⚠️ শর্ত:**\n"
            "• Bot কে সেই channel এর Admin করতে হবে\n"
            "• Bot এর Post Messages permission থাকতে হবে\n\n"
            "**Channel ID কীভাবে পাবেন?**\n"
            "• Channel থেকে যেকোনো message @userinfobot এ forward করুন\n\n"
            "**Format:** `-1001234567890`\n\n"
            "ID পাঠান অথবা /cancel করুন:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_channels":
        await query.edit_message_text(
            "📺 **Force Join Channel Manager**\n\nManage channels that users must join:",
            reply_markup=channel_manager_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # 🔥 NEW: View specific force join channel details
    elif data.startswith("view_channel_"):
        if user_id != ADMIN_ID:
            return
        
        channel_id = int(data.replace("view_channel_", ""))
        channels = get_force_join_channels()
        channel = next((ch for ch in channels if ch['channel_id'] == channel_id), None)
        
        if not channel:
            await query.answer("❌ Channel not found!", show_alert=True)
            return
        
        # Build channel details message
        ch_name = channel.get('username', 'Unknown')
        ch_id = channel['channel_id']
        invite_link = channel.get('invite_link', '')
        is_private = bool(invite_link)
        
        text = f"📺 **Channel Details**\n\n"
        text += f"**Type:** {'🔒 Private' if is_private else '📢 Public'}\n"
        text += f"**Username:** @{ch_name}\n"
        text += f"**ID:** `{ch_id}`\n"
        
        if invite_link:
            text += f"**Invite Link:** `{invite_link}`\n"
        
        text += f"\n━━━━━━━━━━━━━━\n\n"
        text += f"**Actions:**"
        
        keyboard = [
            [InlineKeyboardButton("❌ Remove Channel", callback_data=f"remove_channel_{ch_id}")],
            [InlineKeyboardButton("🔙 Back to Channels", callback_data="admin_channels")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # 🔥 NEW: View specific verified channel details
    elif data.startswith("view_verified_"):
        if user_id != ADMIN_ID:
            return
        
        channel_id = int(data.replace("view_verified_", ""))
        
        # Get channel info from database
        verified_channels = db.verified_channels.find_one({'channel_id': channel_id})
        
        if not verified_channels:
            await query.answer("❌ Channel not found!", show_alert=True)
            return
        
        ch_name = verified_channels.get('channel_name', 'Unknown')
        ch_username = verified_channels.get('channel_username', '')
        
        text = f"✅ **Verified Channel Details**\n\n"
        text += f"**Name:** {ch_name}\n"
        if ch_username:
            text += f"**Username:** @{ch_username}\n"
        text += f"**ID:** `{channel_id}`\n"
        text += f"\n━━━━━━━━━━━━━━\n\n"
        text += f"This channel can send video notifications to admin."
        
        keyboard = [
            [InlineKeyboardButton("❌ Remove Verification", callback_data=f"unverify_channel_{channel_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_verified")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # 🔥 NEW: Unverify channel handler
    elif data.startswith("unverify_channel_"):
        if user_id != ADMIN_ID:
            return
        
        channel_id = int(data.replace("unverify_channel_", ""))
        
        # Remove from verified channels
        result = db.verified_channels.delete_one({'channel_id': channel_id})
        
        if result.deleted_count > 0:
            await query.answer("✅ Channel verification removed!", show_alert=True)
        else:
            await query.answer("❌ Channel not found!", show_alert=True)
        
        # Go back to verified channels list
        verified_count = get_verified_channel_stats()
        await query.edit_message_text(
            f"✅ **Verified Video Channels**\n\n"
            f"Only verified channels can send video notifications.\n\n"
            f"📊 Total Verified: **{verified_count}**\n\n"
            f"Select an option:",
            reply_markup=verified_channels_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # 🔥 NEW: Verified Video Channels
    elif data == "admin_verified":
        verified_count = get_verified_channel_stats()
        await query.edit_message_text(
            f"✅ **Verified Video Channels**\n\n"
            f"Only verified channels can send video notifications.\n\n"
            f"📊 Total Verified: **{verified_count}**\n\n"
            f"Select an option:",
            reply_markup=verified_channels_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_messages":
        await query.edit_message_text(
            "📝 **Message Editor**\n\nSelect a message to edit:",
            reply_markup=message_editor_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_buttons":
        await query.edit_message_text(
            "🔘 **Button Manager**\n\n"
            "Add custom buttons to Welcome or After Video messages.\n\n"
            "You can add:\n"
            "• Channel/Group links\n"
            "• Mini App buttons\n"
            "• Any custom URL\n\n"
            "Select an option:",
            reply_markup=button_manager_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_settings":
        # Get current settings
        mini_app = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
        main_channel = get_setting('main_channel_username', DEFAULT_SETTINGS['main_channel_username'])
        protection = get_setting('video_protection', True)
        bot_name = get_setting('bot_name', DEFAULT_SETTINGS['bot_name'])
        auto_reply = get_setting('auto_reply_enabled', True)
        cleanup = get_setting('message_cleanup_enabled', True)
        welcome_media = get_setting('welcome_media_enabled', False)
        folder_enabled = get_setting('folder_link_enabled', False)
        folder_url = get_setting('folder_link_url', '')
        notfound_btn = get_setting('video_not_found_button', True)
        welcome_voice = get_setting('welcome_voice_enabled', False)
        
        protection_status = "🔒 ON" if protection else "🔓 OFF"
        auto_reply_status = "✅ ON" if auto_reply else "❌ OFF"
        cleanup_status = "✅ ON" if cleanup else "❌ OFF"
        welcome_media_status = "✅ ON" if welcome_media else "❌ OFF"
        folder_status = "✅ ON" if folder_enabled else "❌ OFF"
        notfound_btn_status = "✅ ON" if notfound_btn else "❌ OFF"
        welcome_voice_status = "✅ ON" if welcome_voice else "❌ OFF"
        
        settings_text = f"""⚙️ **Bot Settings**

🎮 **Mini App URL:**
`{mini_app}`

📢 **Main Channel:**
@{main_channel}

🔒 **Video Protection:** {protection_status}
💬 **Auto Reply:** {auto_reply_status}
🧹 **Message Cleanup:** {cleanup_status}
🎬 **Welcome Media:** {welcome_media_status}
🎙️ **Welcome Voice:** {welcome_voice_status}
📁 **Folder Join Link:** {folder_status}
❌ **Video Not Found Button:** {notfound_btn_status}

🤖 **Bot Name:** {bot_name}

Click a button below to edit:"""
        
        await query.edit_message_text(
            settings_text,
            reply_markup=settings_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_stats":
        stats = get_stats()
        
        # Simple short message with verified channels
        text = f"""📊 Bot Stats

👥 Users: {stats['users']}
📹 Videos: {stats['videos']}
🔒 Force Join: {stats['force_join']}
✅ Verified: {stats['verified_channels']}

✅ Running"""
        
        await query.answer(text, show_alert=True)
    
    elif data == "admin_broadcast":
        admin_states[user_id] = {'action': 'broadcast'}
        await query.message.reply_text(
            "📢 **Broadcast Message**\n\n"
            "Send the message you want to broadcast to all users.\n\n"
            "✅ You can send:\n"
            "• Text messages\n"
            "• Photos with captions\n"
            "• Videos with captions\n\n"
            "⚠️ This will be sent to ALL users!\n\n"
            "Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_refresh":
        await query.answer("🔄 Refreshed!")
        # Re-show admin panel with updated stats
        stats = get_stats()
        text = f"""🔧 **CINEFLIX ADMIN PANEL**

📊 **Statistics:**
👥 Total Users: {stats['users']}
🔥 Active Today: {stats['active_today']}
📹 Videos: {stats['videos']}
👁️ Top Views: {stats['top_views']}
🔒 Force Join: {stats['force_join']}
✅ Verified Channels: {stats['verified_channels']}

Select an option below:"""
        await query.edit_message_text(
            text,
            reply_markup=admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_close":
        await query.message.delete()
        await query.answer("Panel closed")
    
    elif data == "add_channel":
        admin_states[user_id] = {'action': 'add_channel'}
        await query.message.reply_text(
            "➕ **Add New Force Join Channel**\n\n"
            "**📢 Public Channel:**\n"
            "`channel_id username [DisplayName]`\n\n"
            "**🔒 Private Channel:**\n"
            "`channel_id invite_link [DisplayName]`\n\n"
            "**🔒 Private + Username:**\n"
            "`channel_id username invite_link [DisplayName]`\n\n"
            "**Examples:**\n\n"
            "Public:\n"
            "`-1001234567890 MyChannel Cineflix Official`\n\n"
            "Private:\n"
            "`-1001234567890 https://t.me/+xxxxxx Cineflix Private`\n\n"
            "💡 DisplayName না দিলে auto-number হবে (Channel 1, Channel 2...)\n"
            "💡 DisplayName = User এর কাছে বাটনে যা দেখাবে\n\n"
            "Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("rename_channel_"):
        channel_id = int(data.replace("rename_channel_", ""))
        ch = force_join_col.find_one({'channel_id': channel_id, 'is_active': True})
        if not ch:
            await query.answer("❌ Channel not found", show_alert=True)
            return
        current_name = ch.get('display_name') or ch.get('username', '')
        admin_states[user_id] = {'action': 'rename_channel', 'channel_id': channel_id}
        await query.message.reply_text(
            f"✏️ **Channel Rename করুন**\n\n"
            f"Current name: **{current_name}**\n\n"
            f"নতুন display name পাঠান।\n"
            f"এটাই user এর কাছে বাটনে দেখাবে।\n\n"
            f"Example: `Cineflix Official`\n\n"
            f"Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("remove_channel_"):
        channel_id = int(data.replace("remove_channel_", ""))
        if remove_force_join_channel(channel_id):
            await query.answer("✅ Channel removed!")
            await button_callback(update, context)  # Refresh list
        else:
            await query.answer("❌ Failed to remove channel", show_alert=True)
    
    # 🔥 NEW: Add Verified Channel
    elif data == "add_verified":
        admin_states[user_id] = {'action': 'add_verified_channel'}
        await query.message.reply_text(
            "✅ **Add Verified Video Channel**\n\n"
            "Send the channel ID where bot is admin.\n"
            "Only verified channels will send video notifications.\n\n"
            "**Format:**\n"
            "`channel_id`\n\n"
            "**Example:**\n"
            "`-1001234567890`\n\n"
            "**💡 How to get Channel ID:**\n"
            "1. Forward any message from channel to @userinfobot\n"
            "2. Copy the channel ID\n"
            "3. Send it here\n\n"
            "Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # 🔥 NEW: Remove Verified Channel
    elif data.startswith("remove_verified_"):
        if user_id != ADMIN_ID:
            return
        channel_id = int(data.replace("remove_verified_", ""))
        result = remove_verified_channel(channel_id)
        await query.answer("✅ Removed!" if result else "❌ Failed", show_alert=not result)
        if result:
            # Refresh verified channels list
            channels = get_verified_channels()
            verified_count = len(channels)
            await query.edit_message_text(
                f"✅ **Verified Video Channels**\n\n"
                f"Only verified channels can send video notifications.\n\n"
                f"📊 Total Verified: **{verified_count}**\n\n"
                f"Select an option:",
                reply_markup=verified_channels_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data.startswith("add_btn_"):
        location = data.replace("add_btn_", "")
        admin_states[user_id] = {'action': 'add_button', 'location': location}
        
        location_name = "Welcome Message" if location == "welcome" else "After Video Message"
        
        await query.message.reply_text(
            f"➕ **Add Button to {location_name}**\n\n"
            f"Send button details in this format:\n"
            f"`Text | URL | Type`\n\n"
            f"**Type** can be:\n"
            f"• `url` - Regular link button\n"
            f"• `webapp` - Mini App button\n\n"
            f"**Examples:**\n"
            f"`📢 Join Channel | https://t.me/MyChannel | url`\n"
            f"`🎮 Open App | https://myapp.com/ | webapp`\n"
            f"`👥 Join Group | https://t.me/+grouplink | url`\n\n"
            f"Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("view_btn_"):
        location = data.replace("view_btn_", "")
        buttons = get_buttons(location)
        
        location_name = "Welcome Message" if location == "welcome" else "After Video Message"
        
        if not buttons:
            await query.answer(f"No custom buttons for {location_name}", show_alert=True)
            return
        
        # Create keyboard with button list
        keyboard = []
        for btn in buttons:
            btn_id = str(btn['_id'])
            btn_type_icon = "🌐" if btn['type'] == 'web_app' else "🔗"
            keyboard.append([
                InlineKeyboardButton(f"{btn_type_icon} {btn['text']}", callback_data=f"dummy"),
                InlineKeyboardButton("🗑️", callback_data=f"remove_btn_{btn_id}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_buttons")])
        
        await query.edit_message_text(
            f"📋 **{location_name} Buttons**\n\n"
            f"Total: {len(buttons)} button(s)\n\n"
            f"Click 🗑️ to remove a button:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("remove_btn_"):
        button_id = data.replace("remove_btn_", "")
        if remove_button(button_id):
            await query.answer("✅ Button removed!")
            await button_callback(update, context)
        else:
            await query.answer("❌ Failed to remove button", show_alert=True)
    
    elif data.startswith("edit_msg_"):
        msg_key = data.replace("edit_msg_", "")
        admin_states[user_id] = {'action': 'edit_message', 'key': msg_key}
        
        current_msg = get_message(msg_key)
        await query.message.reply_text(
            f"✏️ **Editing {msg_key.replace('_', ' ').title()}**\n\n"
            f"Current message:\n\n{current_msg}\n\n"
            f"Send the new message text or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("setting_"):
        setting_key = data.replace("setting_", "")
        
        # Handle toggles
        if setting_key == "protection":
            current = get_setting('video_protection', True)
            new_val = not current
            set_setting('video_protection', new_val)
            
            status = "🔒 ON" if new_val else "🔓 OFF"
            await query.answer(f"Video Protection: {status}")
            await button_callback(update, context)
            return
        
        elif setting_key == "auto_reply":
            current = get_setting('auto_reply_enabled', True)
            new_val = not current
            set_setting('auto_reply_enabled', new_val)
            
            status = "✅ ON" if new_val else "❌ OFF"
            await query.answer(f"Auto Reply: {status}")
            await button_callback(update, context)
            return
        
        elif setting_key == "cleanup":
            current = get_setting('message_cleanup_enabled', True)
            new_val = not current
            set_setting('message_cleanup_enabled', new_val)
            
            status = "✅ ON" if new_val else "❌ OFF"
            await query.answer(f"Message Cleanup: {status}")
            await button_callback(update, context)
            return

        elif setting_key == "notfound_btn":
            current = get_setting('video_not_found_button', True)
            new_val = not current
            set_setting('video_not_found_button', new_val)
            status = "✅ ON" if new_val else "❌ OFF"
            await query.answer(f"Video Not Found Button: {status}")
            await button_callback(update, context)
            return
        
        # NEW: Welcome Media management
        elif setting_key == "welcome_media":
            current = get_setting('welcome_media_enabled', False)
            
            if not current:
                # Currently OFF, prompt to upload media
                admin_states[user_id] = {'action': 'upload_welcome_media'}
                await query.message.reply_text(
                    "🎬 **Upload Welcome Media**\n\n"
                    "Send me a photo, GIF, or short video that will be shown when users use /start.\n\n"
                    "📝 **Tips:**\n"
                    "• Keep videos under 5 seconds\n"
                    "• File size under 5 MB recommended\n"
                    "• GIFs work great for animations!\n\n"
                    "Or /cancel to cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Currently ON, toggle OFF
                set_setting('welcome_media_enabled', False)
                await query.answer("✅ Welcome Media: OFF")
                await button_callback(update, context)
            return
        
        # 🎙️ NEW: Welcome Voice management
        elif setting_key == "welcome_voice":
            current = get_setting('welcome_voice_enabled', False)
            
            if not current:
                # Currently OFF → ask admin to upload voice
                admin_states[user_id] = {'action': 'upload_welcome_voice'}
                await query.message.reply_text(
                    "🎙️ **Welcome Voice Setup**\n\n"
                    "এখন একটা voice message বা audio file পাঠাও।\n"
                    "User /start দিলে এই voice টা সবার আগে দেখাবে — ঠিক recorded voice-এর মতো! 🎤\n\n"
                    "✅ **কী কী চলবে:**\n"
                    "• Telegram voice message (🎤 রেকর্ড করা)\n"
                    "• MP3, OGG, WAV, M4A audio file\n\n"
                    "⚠️ Short voice (30 সেকেন্ড বা কম) best!\n\n"
                    "পাঠাও অথবা /cancel করো",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Currently ON → toggle OFF
                set_setting('welcome_voice_enabled', False)
                await query.answer("🎙️ Welcome Voice: OFF")
                await button_callback(update, context)
            return
        
        # NEW: Folder Link management
        elif setting_key == "folder_link":
            current_enabled = get_setting('folder_link_enabled', False)
            current_url = get_setting('folder_link_url', '')
            
            if not current_enabled or not current_url:
                # Ask for folder URL
                admin_states[user_id] = {'action': 'set_folder_link'}
                await query.message.reply_text(
                    "📁 **Setup Folder Join Link**\n\n"
                    "**How to create a folder link:**\n"
                    "1. Go to Telegram Settings > Folders\n"
                    "2. Create a folder with all your private channels\n"
                    "3. Share the folder and copy the link\n\n"
                    "**Example link format:**\n"
                    "`https://t.me/addlist/xxxxxxxxxxxxx`\n\n"
                    "Send me your folder link, or /cancel to cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Toggle OFF
                set_setting('folder_link_enabled', False)
                await query.answer("✅ Folder Link: OFF (Individual channels will be shown)")
                await button_callback(update, context)
            return
        
        # For other settings, ask for input
        admin_states[user_id] = {'action': 'edit_setting', 'key': setting_key}
        
        # Map callback data to actual setting keys
        setting_map = {
            'mini_app': 'mini_app_url',
            'main_channel': 'main_channel_username',
            'bot_name': 'bot_name'
        }
        
        actual_key = setting_map.get(setting_key, setting_key)
        current = get_setting(actual_key)
        
        # Provide helpful hints
        hints = {
            'mini_app': (
                "দুই ধরনের link দিতে পারবে:\n"
                "• **Telegram Mini App:** `https://t.me/YourBot/appname`\n"
                "• **Vercel/Web App:** `https://yourapp.vercel.app/`\n\n"
                "যেটা দেবে সেটাই Start, Video, Not Found, Auto Reply — সব জায়গায় কাজ করবে।"
            ),
            'main_channel': "Example: YourChannel (without @)",
            'bot_name': "Example: CINEFLIX"
        }
        
        hint_text = f"\n\n💡 {hints.get(setting_key, '')}" if setting_key in hints else ""
        
        await query.message.reply_text(
            f"⚙️ **Editing {actual_key.replace('_', ' ').title()}**\n\n"
            f"Current value: `{current}`{hint_text}\n\n"
            f"Send the new value or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Store the actual key for later use
        admin_states[user_id]['actual_key'] = actual_key

    # ===================== 🎙️ VOICE MANAGER CALLBACKS =====================
    elif data == "admin_voice_manager":
        if user_id != ADMIN_ID:
            return
        channels = get_voice_channels()
        active = get_active_voice_channel()
        active_name = active.get('channel_name', 'কোনোটি সেট নেই') if active else 'কোনোটি সেট নেই'

        text = (
            "🎙️ **Voice Manager**\n\n"
            f"✅ **Active Channel:** {active_name}\n\n"
            "Audio file পাঠালে এই channel এ Voice Message হিসেবে post হবে।\n"
            "কেউ বুঝতে পারবে না এটা ফাইল থেকে এসেছে!\n\n"
            "👇 Channel সেট করুন, তারপর Audio পাঠান:"
        )
        await query.edit_message_text(
            text,
            reply_markup=voice_manager_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "voice_add_channel":
        if user_id != ADMIN_ID:
            return
        admin_states[user_id] = {'action': 'add_voice_channel'}
        await query.message.reply_text(
            "🎙️ **Voice Channel যোগ করুন**\n\n"
            "যে channel এ Voice Message পাঠাতে চান সেই channel এর **ID** পাঠান।\n\n"
            "⚠️ **শর্ত:** Bot কে সেই channel এর Admin করতে হবে\n\n"
            "**Channel ID কীভাবে পাবেন?**\n"
            "• Channel থেকে যেকোনো message @userinfobot এ forward করুন\n\n"
            "**Format:** `-1001234567890`\n\n"
            "ID পাঠান অথবা /cancel করুন:",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("voice_select_"):
        if user_id != ADMIN_ID:
            return
        ch_id = int(data.replace("voice_select_", ""))
        set_selected_voice_channel(ch_id)
        await query.answer("✅ Channel সেট হয়েছে!")
        # Refresh
        channels = get_voice_channels()
        active = get_active_voice_channel()
        active_name = active.get('channel_name', 'কোনোটি সেট নেই') if active else 'কোনোটি সেট নেই'
        text = (
            "🎙️ **Voice Manager**\n\n"
            f"✅ **Active Channel:** {active_name}\n\n"
            "Audio file পাঠালে এই channel এ Voice Message হিসেবে post হবে।\n\n"
            "👇 Channel সেট করুন, তারপর Audio পাঠান:"
        )
        await query.edit_message_text(text, reply_markup=voice_manager_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("voice_remove_"):
        if user_id != ADMIN_ID:
            return
        ch_id = int(data.replace("voice_remove_", ""))
        if remove_voice_channel(ch_id):
            await query.answer("✅ Channel remove হয়েছে!")
        else:
            await query.answer("❌ Remove করা যায়নি!", show_alert=True)
        channels = get_voice_channels()
        active = get_active_voice_channel()
        active_name = active.get('channel_name', 'কোনোটি সেট নেই') if active else 'কোনোটি সেট নেই'
        text = (
            "🎙️ **Voice Manager**\n\n"
            f"✅ **Active Channel:** {active_name}\n\n"
            "Audio file পাঠালে এই channel এ Voice Message হিসেবে post হবে।\n\n"
            "👇 Channel সেট করুন, তারপর Audio পাঠান:"
        )
        await query.edit_message_text(text, reply_markup=voice_manager_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data == "voice_send_now":
        if user_id != ADMIN_ID:
            return
        active = get_active_voice_channel()
        if not active:
            await query.answer("❌ আগে একটা Channel সেট করুন!", show_alert=True)
            return
        admin_states[user_id] = {'action': 'voice_upload'}
        ch_name = active.get('channel_name', 'Unknown')
        await query.message.reply_text(
            f"🎙️ **Voice Upload Mode**\n\n"
            f"✅ Target Channel: **{ch_name}**\n\n"
            f"এখন যেকোনো Audio File পাঠান:\n"
            f"• MP3, WAV, OGG, M4A যেকোনো format\n"
            f"• Bot নিজেই convert করে Voice Message বানাবে\n"
            f"• চ্যানেলে রেকর্ড করা ভয়েসের মতো দেখাবে ✅\n\n"
            f"Audio পাঠান অথবা /cancel করুন:",
            parse_mode=ParseMode.MARKDOWN
        )

    # ===================== 📢 POST MANAGER CALLBACKS =====================
    elif data == "admin_post_manager":
        if user_id != ADMIN_ID:
            return
        channels = get_post_manager_channels()
        on_count = sum(1 for ch in channels if ch.get('is_active', True))
        off_count = len(channels) - on_count
        text = (
            f"📢 **Post Manager**\n\n"
            f"🟢 ON: **{on_count}টি** | 🔴 OFF: **{off_count}টি**\n\n"
            f"🟢 ON — channel এ post হলে admin কে আসবে\n"
            f"🔴 OFF — কিছুই হবে না, admin কে disturb করবে না\n\n"
            f"👇 Channel বেছে নিন:"
        )
        await query.edit_message_text(text, reply_markup=post_manager_channel_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif (data.startswith("pm_addbtn_") or data.startswith("pm_rmbtn_") or
          data.startswith("pm_apply_") or data.startswith("pm_postasis_") or
          data.startswith("pm_delete_") or data.startswith("pm_editcap_") or
          data.startswith("pm_remove_") or data.startswith("pm_toggle_") or
          data == "pm_add_channel"):
        if user_id != ADMIN_ID:
            return
        await handle_pm_callbacks(data, query, context, user_id)

    # ===================== 📌 PINNED BUTTON CALLBACKS =====================
    elif data == "admin_pinned_btn":
        if user_id != ADMIN_ID:
            return
        channels = get_pinned_channels()
        count = len(channels)
        text = (
            f"📌 **Pinned Button Manager**\n\n"
            f"📡 Active Channels: **{count}টি**\n\n"
            f"✅ Channel এর pinned message এ buttons লাগাতে পারবেন\n"
            f"✅ URL বা Mini App link — যেকোনো button\n"
            f"✅ সব user সবসময় pinned message এ দেখতে পাবে\n\n"
            f"👇 Channel বেছে নিন:"
        )
        await query.edit_message_text(text, reply_markup=pinned_manager_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif (data == "pin_add_channel" or data.startswith("pin_manage_") or
          data.startswith("pin_add_btn_") or data.startswith("pin_remove_btn_") or
          data.startswith("pin_apply_") or data.startswith("pin_delete_channel_")):
        if user_id != ADMIN_ID:
            return
        await handle_pinned_callbacks(data, query, context, user_id)

# ===================== CHANNEL POST HANDLER =====================
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle videos posted in channels - 🔥 WITH VERIFICATION CHECK"""
    try:
        logger.info(f"📥 Channel post received")
        
        message = update.channel_post or update.message
        if not message:
            return
        
        # NEW: Check for all media types including photos
        has_video = bool(message.video)
        has_document = bool(message.document)
        has_animation = bool(message.animation)
        has_photo = bool(message.photo)
        has_text = bool(message.text)
        has_audio = bool(message.audio)

        logger.info(f"📝 Message type - Video: {has_video}, Document: {has_document}, Animation: {has_animation}, Photo: {has_photo}, Text: {has_text}")

        # Get channel info safely
        channel_id = message.chat.id
        message_id = message.message_id
        channel_name = message.chat.title or "Unknown"

        # 📢 POST MANAGER: Check first (handles ALL post types including text)
        if is_post_manager_channel(channel_id):
            logger.info(f"📢 Post Manager channel: {channel_name} ({channel_id})")
            await handle_post_manager_channel_post(message, context)
            return

        # For verified channel system - only media
        if not (has_video or has_document or has_animation or has_photo):
            logger.info("⏭️ Not a media file, skipping")
            return
        
        # 🔥 Log who posted (for debugging)
        if message.from_user:
            logger.info(f"👤 Posted by user: {message.from_user.first_name} (admin signature)")
        else:
            logger.info(f"📢 Posted by channel itself")
        
        # 🔥 CHECK IF CHANNEL IS VERIFIED — not verified হলে ignore
        if not is_channel_verified(channel_id):
            logger.info(f"🚫 Channel {channel_name} ({channel_id}) is NOT VERIFIED - Ignoring")
            return
        
        logger.info(f"✅ Channel {channel_name} ({channel_id}) IS VERIFIED - Processing media")
        
        # NEW: Detect media type
        media_type = "video"  # default
        media_icon = "🎬"
        if has_photo:
            media_type = "photo"
            media_icon = "📸"
        elif has_animation:
            media_type = "animation"
            media_icon = "🎞️"
        elif has_document:
            media_type = "document"
            media_icon = "📄"
        
        logger.info(f"{media_icon} Processing {media_type} - Channel: {channel_name} ({channel_id}), Message ID: {message_id}")
        
        # Save to database with media type
        save_video(channel_id, message_id, channel_name, media_type)
        logger.info(f"💾 {media_type.title()} saved to database")
        
        # Get bot username for deep link
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        
        # Create admin notification - USE HTML instead of MARKDOWN to avoid parsing errors
        deep_link = f"https://t.me/{bot_username}?start={message_id}"
        
        # Escape HTML special characters in channel name
        safe_channel_name = html.escape(channel_name)
        
        # Send notification with HTML format (more reliable than Markdown)
        info_text = f"""{media_icon} <b>New {media_type.title()} Uploaded!</b>

📺 Channel: {safe_channel_name}
📋 Message ID: <code>{message_id}</code>
📁 Type: {media_type.upper()}

🌐 Direct Link:
{deep_link}

✅ {media_type.title()} saved to database!
Users can now access this content!

👇 <b>Tap the number below to copy:</b>"""
        
        logger.info(f"📤 Sending notification to admin {ADMIN_ID}")
        
        # First message with info (using HTML parse mode)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=info_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        # Second message with ONLY the copyable shortcode
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"<code>{message_id}</code>",
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ Successfully notified admin about {media_type} {message_id}")
        
        # 🔥 Auto-forward to ALL enabled forward channels
        fwd_channels = get_forward_channels()
        if fwd_channels:
            for fwd_ch in fwd_channels:
                if not fwd_ch.get('enabled', True):
                    continue  # Skip if toggled OFF
                fwd_ch_id = fwd_ch['channel_id']
                if fwd_ch_id == channel_id:
                    continue  # Don't forward to same channel
                try:
                    # copy_message ব্যবহার করো — protect content থাকলেও কাজ করে
                    await context.bot.copy_message(
                        chat_id=fwd_ch_id,
                        from_chat_id=channel_id,
                        message_id=message_id
                    )
                    logger.info(f"✅ Channel post copied to {fwd_ch_id}")
                except Exception as copy_err:
                    try:
                        await context.bot.forward_message(
                            chat_id=fwd_ch_id,
                            from_chat_id=channel_id,
                            message_id=message_id
                        )
                        logger.info(f"✅ Channel post forwarded to {fwd_ch_id}")
                    except Exception as fwd_err:
                        logger.error(f"❌ Failed copy+forward to {fwd_ch_id}: {fwd_err}")
        
    except Exception as e:
        logger.error(f"❌ Error in channel_post handler: {e}", exc_info=True)

# ===================== ADMIN MESSAGE HANDLER =====================
async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text messages for editing"""
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    
    # Check if this is a broadcast message (admin sending to users)
    if user_id in admin_states and admin_states[user_id].get('action') == 'broadcast':
        await handle_broadcast(update, context)
        return
    
    # Auto-reply for non-admin users
    if user_id != ADMIN_ID:
        auto_reply_enabled = get_setting('auto_reply_enabled', True)
        if auto_reply_enabled:
            keyboard = [[make_mini_app_button("🎮 Open Mini App")]]
            
            await update.message.reply_text(
                get_message('auto_reply'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # 🔥 NEW: Admin sends video/document directly to bot (no state needed)
    if user_id == ADMIN_ID and update.message:
        has_video = bool(update.message.video)
        has_document = bool(update.message.document)
        has_animation = bool(update.message.animation)
        
        # Only handle if NOT in any special state
        if (has_video or has_document or has_animation) and user_id not in admin_states:
            await handle_admin_direct_upload(update, context)
            return
    
    # Admin-specific handlers
    if user_id not in admin_states:
        return
    
    # 🎙️ VOICE MANAGER: Handle audio file upload
    if admin_states.get(user_id, {}).get('action') == 'voice_upload':
        if update.message and (update.message.audio or update.message.voice or
                               (update.message.document and update.message.document.mime_type and
                                'audio' in update.message.document.mime_type)):
            await handle_voice_upload(update, context)
            return
        elif update.message and update.message.text and update.message.text != '/cancel':
            await update.message.reply_text(
                "❌ Audio file পাঠান!\nMP3, WAV, OGG, M4A যেকোনো format চলবে।\n\n/cancel করতে লিখুন /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # 🎙️ NEW: Handle welcome voice upload
    if admin_states[user_id].get('action') == 'upload_welcome_voice':
        voice_file_id = None
        
        if update.message.voice:
            voice_file_id = update.message.voice.file_id
        elif update.message.audio:
            voice_file_id = update.message.audio.file_id
        elif update.message.document and update.message.document.mime_type and 'audio' in update.message.document.mime_type:
            voice_file_id = update.message.document.file_id
        
        if voice_file_id:
            # Save to settings
            set_setting('welcome_voice_file_id', voice_file_id)
            set_setting('welcome_voice_enabled', True)
            
            del admin_states[user_id]
            
            await update.message.reply_text(
                "✅ **Welcome Voice Set Successfully!**\n\n"
                "এখন থেকে প্রতিটা user /start দিলে এই voice message টা পাবে।\n\n"
                "🔧 বন্ধ করতে: Settings → 🎙️ Welcome Voice → আবার চাপো",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"✅ Welcome voice uploaded: {voice_file_id}")
        else:
            await update.message.reply_text(
                "❌ Voice বা Audio file পাঠাও!\n\n"
                "• Telegram voice message রেকর্ড করে পাঠাও 🎤\n"
                "• অথবা MP3/OGG/WAV file পাঠাও\n\n"
                "/cancel করতে লিখুন /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # NEW: Handle welcome media upload (photo/animation/video)
    if admin_states[user_id].get('action') == 'upload_welcome_media':
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            media_type = 'photo'
        elif update.message.animation:
            file_id = update.message.animation.file_id
            media_type = 'animation'
        elif update.message.video:
            file_id = update.message.video.file_id
            media_type = 'video'
        else:
            await update.message.reply_text(
                "❌ Please send a photo, GIF, or video!\n\nOr /cancel to cancel",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Save to settings
        set_setting('welcome_media_file_id', file_id)
        set_setting('welcome_media_type', media_type)
        set_setting('welcome_media_enabled', True)
        
        await update.message.reply_text(
            f"✅ **Welcome {media_type.title()} Saved!**\n\n"
            f"Users will now see this {media_type} when they use /start.\n\n"
            f"You can toggle it on/off anytime from Settings.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        del admin_states[user_id]
        logger.info(f"✅ Welcome media uploaded: {media_type}")
        return
    
    text = update.message.text if update.message else None
    state = admin_states[user_id]
    
    if text == "/cancel":
        del admin_states[user_id]
        await update.message.reply_text("❌ Cancelled")
        return
    
    # Text নেই মানে video/photo/audio পাঠিয়েছে state এ থাকা অবস্থায়
    # যেসব state এ শুধু text দরকার সেগুলোতে warn করো
    text_only_states = [
        'add_forward_channel', 'add_verified_channel', 'add_pinned_channel',
        'rename_channel', 'add_channel', 'edit_message', 'edit_setting',
        'set_folder_link', 'add_post_manager_channel'
    ]
    if text is None and state.get('action') in text_only_states:
        await update.message.reply_text(
            "❌ Text message পাঠান।\n\nCancel করতে /cancel লিখুন।"
        )
        return
    
    # 🎙️ VOICE MANAGER: Handle adding voice channel
    if state['action'] == 'add_voice_channel':
        try:
            raw = text.strip().replace(' ', '')
            if raw.lstrip('-').isdigit():
                channel_id = int(raw)
                if channel_id > 0 and len(str(channel_id)) >= 10:
                    channel_id = int(f"-100{channel_id}")
            else:
                await update.message.reply_text(
                    "❌ **Invalid Channel ID!**\n\n"
                    "Channel ID number হতে হবে।\n"
                    "Example: `-1001234567890`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            channel_id = channel_id
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or f"Channel {channel_id}"

                # Verify bot is admin
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ **Bot এই channel এর Admin না!**\n\n"
                        "প্রথমে Bot কে channel এ Admin করুন।\n\n"
                        "আবার ID পাঠান অথবা /cancel করুন:",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

                if add_voice_channel(channel_id, channel_name):
                    set_selected_voice_channel(channel_id)
                    await update.message.reply_text(
                        f"✅ **Voice Channel সেট হয়েছে!**\n\n"
                        f"**Channel:** {channel_name}\n"
                        f"**ID:** `{channel_id}`\n\n"
                        f"এখন 🎙️ Voice Manager এ গিয়ে Audio পাঠান।",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🎙️ Voice Manager", callback_data="admin_voice_manager")
                        ]])
                    )
                    del admin_states[user_id]
                else:
                    await update.message.reply_text("❌ Channel add করা যায়নি।")
            except BadRequest as e:
                await update.message.reply_text(
                    f"❌ Channel পাওয়া যায়নি! নিশ্চিত করুন Bot সেই channel এর Admin।\n\nError: {e}"
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Channel ID অবশ্যই number হতে হবে!\nExample: `-1001234567890`"
            )
        return

    # 📢 POST MANAGER: Compose text post from bot
    if state['action'] == 'pm_compose_text':
        ch_id = state['channel_id']
        ch_name = state.get('channel_name', str(ch_id))
        import time
        code = f"pp_{int(time.time())}"
        pending_posts_col.insert_one({
            'code': code, 'channel_id': ch_id, 'message_id': None,
            'media_type': 'text', 'file_id': None, 'caption': None, 'text': text,
            'buttons': [], 'status': 'pending', 'created_at': datetime.utcnow()
        })
        del admin_states[user_id]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Button যোগ করুন", callback_data=f"pm_addbtn_composed_{code}")],
            [InlineKeyboardButton("✅ Post করুন", callback_data=f"pm_send_composed_{code}")],
            [InlineKeyboardButton("🗑️ Cancel", callback_data="admin_post_manager")]
        ])
        await update.message.reply_text(
            f"📝 **Preview — {ch_name}**\n\n{text}\n\nButton যোগ করবেন, নাকি সরাসরি post করবেন?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # 📢 POST MANAGER: Compose photo/video post from bot
    if state['action'] in ('pm_compose_photo', 'pm_compose_video'):
        ch_id = state['channel_id']
        ch_name = state.get('channel_name', str(ch_id))
        mtype = 'photo' if state['action'] == 'pm_compose_photo' else 'video'
        file_id = None
        caption = (update.message.caption or '') if update.message else ''
        if update.message and mtype == 'photo' and update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message and mtype == 'video' and update.message.video:
            file_id = update.message.video.file_id
        elif update.message and mtype == 'video' and update.message.document:
            # document হিসেবে পাঠানো video ও accept করো
            file_id = update.message.document.file_id
        else:
            await update.message.reply_text(f"❌ {'Photo' if mtype=='photo' else 'Video'} পাঠান!\n\n/cancel করতে লিখুন /cancel")
            return
        import time
        code = f"pp_{int(time.time())}"
        pending_posts_col.insert_one({
            'code': code, 'channel_id': ch_id, 'message_id': None,
            'media_type': mtype, 'file_id': file_id, 'caption': caption, 'text': None,
            'buttons': [], 'status': 'pending', 'created_at': datetime.utcnow()
        })
        del admin_states[user_id]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Button যোগ করুন", callback_data=f"pm_addbtn_composed_{code}")],
            [InlineKeyboardButton("✅ Post করুন", callback_data=f"pm_send_composed_{code}")],
            [InlineKeyboardButton("🗑️ Cancel", callback_data="admin_post_manager")]
        ])
        await update.message.reply_text(
            f"{'🖼️' if mtype=='photo' else '🎬'} **Preview ready — {ch_name}**\n\nButton যোগ করবেন, নাকি সরাসরি post করবেন?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # 📢 POST MANAGER: Add button to composed post
    if state['action'] == 'pm_add_composed_button':
        code = state['code']
        parts = text.split('|')
        if len(parts) != 3:
            await update.message.reply_text("❌ Format: `নাম | লিঙ্ক | type`", parse_mode=ParseMode.MARKDOWN)
            return
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        btn_type = parts[2].strip().lower()
        if btn_type not in ['url', 'webapp']:
            await update.message.reply_text("❌ type: `url` বা `webapp`", parse_mode=ParseMode.MARKDOWN)
            return
        if not btn_url.startswith('http'):
            await update.message.reply_text("❌ URL http দিয়ে শুরু হতে হবে!")
            return
        if btn_type == 'webapp':
            btn_type = 'web_app'
        post = pending_posts_col.find_one({'code': code, 'status': 'pending'})
        if not post:
            await update.message.reply_text("❌ Post পাওয়া যায়নি!")
            del admin_states[user_id]
            return
        buttons = post.get('buttons', [])
        buttons.append({'text': btn_text, 'url': btn_url, 'type': btn_type})
        pending_posts_col.update_one({'code': code}, {'$set': {'buttons': buttons}})
        del admin_states[user_id]
        await update.message.reply_text(
            f"✅ Button যোগ হয়েছে: `{btn_text}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ আরো Button", callback_data=f"pm_addbtn_composed_{code}")],
                [InlineKeyboardButton("✅ Post করুন", callback_data=f"pm_send_composed_{code}")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # 📢 POST MANAGER: Add channel
    if state['action'] == 'add_post_manager_channel':
        try:
            raw = text.strip().replace(' ', '')
            if raw.lstrip('-').isdigit():
                channel_id = int(raw)
                if channel_id > 0 and len(str(channel_id)) >= 10:
                    channel_id = int(f"-100{channel_id}")
            else:
                await update.message.reply_text(
                    "❌ **Invalid Channel ID!**\n\n"
                    "Channel ID number হতে হবে।\n"
                    "Example: `-1001234567890`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            channel_id = channel_id
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or f"Channel {channel_id}"
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ **Bot এই channel এর Admin না!**\n\nBot কে Admin করুন তারপর আবার try করুন।",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                if add_post_manager_channel(channel_id, channel_name):
                    await update.message.reply_text(
                        f"✅ **Post Manager Channel যোগ হয়েছে!**\n\n"
                        f"**Channel:** {channel_name}\n**ID:** `{channel_id}`\n\n"
                        f"এখন থেকে এই channel এ যা post হবে admin কে forward করবে।",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("📢 Post Manager", callback_data="admin_post_manager")
                        ]])
                    )
                    del admin_states[user_id]
            except BadRequest as e:
                await update.message.reply_text(f"❌ Channel পাওয়া যায়নি!\n\nError: {e}")
        except ValueError:
            await update.message.reply_text("❌ Channel ID number হতে হবে! Example: `-1001234567890`")
        return

    # 📌 PINNED BUTTON: Add channel
    if state['action'] == 'add_pinned_channel':
        try:
            raw = text.strip().replace(' ', '')
            if raw.lstrip('-').isdigit():
                channel_id = int(raw)
                if channel_id > 0 and len(str(channel_id)) >= 10:
                    channel_id = int(f"-100{channel_id}")
            else:
                await update.message.reply_text(
                    "❌ **Invalid Channel ID!**\n\n"
                    "Channel ID number হতে হবে।\n"
                    "Example: `-1001234567890`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            channel_id = channel_id
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or f"Channel {channel_id}"
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ **Bot এই channel এর Admin না!**\n\nBot কে Admin করুন তারপর আবার try করুন।",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                save_pinned_buttons(channel_id, [], channel_name=channel_name)
                await update.message.reply_text(
                    f"✅ **Pinned Button Channel যোগ হয়েছে!**\n\n"
                    f"**Channel:** {channel_name}\n**ID:** `{channel_id}`\n\n"
                    f"এখন Pinned Button Manager এ গিয়ে button যোগ করুন।",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📌 Pinned Button", callback_data="admin_pinned_btn")
                    ]])
                )
                del admin_states[user_id]
            except BadRequest as e:
                await update.message.reply_text(f"❌ Channel পাওয়া যায়নি!\n\nError: {e}")
        except ValueError:
            await update.message.reply_text("❌ Channel ID number হতে হবে! Example: `-1001234567890`")
        return

    # 📌 PINNED BUTTON: Add button
    if state['action'] == 'add_pinned_button':
        ch_id = state['channel_id']
        parts = text.split('|')
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Format ঠিক নেই!\n\n`নাম | লিঙ্ক | type`\n\nExample:\n`♻️ BACKUP | https://t.me/ch | url`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        btn_type = parts[2].strip().lower()
        if btn_type not in ['url', 'webapp']:
            await update.message.reply_text("❌ type হবে `url` অথবা `webapp`", parse_mode=ParseMode.MARKDOWN)
            return
        if not btn_url.startswith('http'):
            await update.message.reply_text("❌ লিঙ্ক http দিয়ে শুরু হতে হবে!")
            return
        if btn_type == 'webapp':
            btn_type = 'web_app'
        buttons = get_pinned_buttons(ch_id)
        buttons.append({'text': btn_text, 'url': btn_url, 'type': btn_type})
        save_pinned_buttons(ch_id, buttons)
        await update.message.reply_text(
            f"✅ **Button যোগ হয়েছে!**\n\n`{btn_text}` → `{btn_url}`\n\n"
            f"আরো button যোগ করতে আবার পাঠান, অথবা Apply করুন।",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📌 Pinned Manager", callback_data=f"pin_manage_{ch_id}")
            ]])
        )
        del admin_states[user_id]
        return

    # 📢 POST MANAGER: Add button to post
    if state['action'] == 'pm_add_button':
        code = state['code']
        parts = text.split('|')
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Format ঠিক নেই!\n\n`নাম | লিঙ্ক | type`\n\nExample:\n`🎮 Open App | https://app.com | webapp`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        btn_type = parts[2].strip().lower()
        if btn_type not in ['url', 'webapp']:
            await update.message.reply_text("❌ type হবে `url` অথবা `webapp`", parse_mode=ParseMode.MARKDOWN)
            return
        if not btn_url.startswith('http'):
            await update.message.reply_text("❌ লিঙ্ক http দিয়ে শুরু হতে হবে!")
            return
        if btn_type == 'webapp':
            btn_type = 'web_app'
        post = get_pending_post(code)
        if not post:
            await update.message.reply_text("❌ Post পাওয়া যায়নি!")
            del admin_states[user_id]
            return
        buttons = post.get('buttons', [])
        buttons.append({'text': btn_text, 'url': btn_url, 'type': btn_type})
        update_pending_post_buttons(code, buttons)
        del admin_states[user_id]
        await update.message.reply_text(
            f"✅ **Button যোগ হয়েছে!**\n\n`{btn_text}`\n\nআরো button যোগ করতে আবার চাপুন, অথবা Apply করুন।",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ আরো Button যোগ করুন", callback_data=f"pm_addbtn_{code}")],
                [InlineKeyboardButton("✅ Apply করুন", callback_data=f"pm_apply_{code}")]
            ])
        )
        return

    # 📢 POST MANAGER: Edit caption
    if state['action'] == 'pm_edit_caption':
        code = state['code']
        post = get_pending_post(code)
        if not post:
            await update.message.reply_text("❌ Post পাওয়া যায়নি!")
            del admin_states[user_id]
            return
        try:
            await context.bot.edit_message_caption(
                chat_id=post['channel_id'],
                message_id=post['message_id'],
                caption=text,
                parse_mode=ParseMode.MARKDOWN
            )
            del admin_states[user_id]
            await update.message.reply_text(
                "✅ **Caption update হয়েছে!**\n\nএখন button যোগ করতে পারবেন।",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Button যোগ করুন", callback_data=f"pm_addbtn_{code}")
                ]])
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Caption update করা যায়নি!\n\n`{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        return

    # NEW: Handle folder link setup
    if state['action'] == 'set_folder_link':
        text = text.strip()
        
        # Validate folder link format
        if not text.startswith('https://t.me/addlist/'):
            await update.message.reply_text(
                "❌ **Invalid Folder Link!**\n\n"
                "Folder links must start with:\n"
                "`https://t.me/addlist/`\n\n"
                "Please send a valid folder link or /cancel to cancel",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Save folder link settings
        set_setting('folder_link_url', text)
        set_setting('folder_link_enabled', True)
        
        await update.message.reply_text(
            "✅ **Folder Link Saved!**\n\n"
            f"URL: `{text}`\n\n"
            "Users will now see a single '📁 Join All Channels (1-Click)' button instead of individual channel buttons.\n\n"
            "You can toggle it on/off anytime from Settings.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        del admin_states[user_id]
        logger.info(f"✅ Folder link configured: {text}")
        return
    
    # 🔥 NEW: Handle forward channel setup
    if state['action'] == 'add_forward_channel':
        try:
            raw = text.strip().replace(' ', '')
            if raw.lstrip('-').isdigit():
                channel_id = int(raw)
                # positive 10+ digit → add -100 prefix
                if channel_id > 0 and len(str(channel_id)) >= 10:
                    channel_id = int(f"-100{channel_id}")
            else:
                await update.message.reply_text(
                    "❌ **Invalid Channel ID!**\n\n"
                    "Channel ID number হতে হবে।\n"
                    "Example: `-1001234567890`\n\n"
                    "আবার পাঠান অথবা /cancel করুন:",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            channel_id = channel_id  # already set above
            
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or f"Channel {channel_id}"
                
                # Verify bot is admin
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ **Bot এই channel এর Admin না!**\n\n"
                        "প্রথমে Bot কে channel এ Admin করুন, তারপর আবার try করুন।\n\n"
                        "Channel ID আবার পাঠান অথবা /cancel করুন:",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Add to forward channels collection (unlimited)
                if add_forward_channel(channel_id, channel_name):
                    total = get_forward_channel_count()
                    await update.message.reply_text(
                        f"✅ **Forward Channel Add হয়েছে!**\n\n"
                        f"**Channel:** {channel_name}\n"
                        f"**ID:** `{channel_id}`\n\n"
                        f"মোট Forward Channels: **{total}টি**\n\n"
                        f"আরো channel add করতে আবার channel ID পাঠান।\n"
                        f"শেষ হলে /cancel করুন।",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # Don't delete state — allow adding more channels
                else:
                    await update.message.reply_text("❌ Channel add করা যায়নি। আবার try করুন।")
                    
            except BadRequest as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg:
                    await update.message.reply_text(
                        "❌ **Channel পাওয়া যায়নি!**\n\n"
                        "নিশ্চিত করুন:\n"
                        "• Channel ID সঠিক আছে\n"
                        "• Bot channel এ add করা আছে\n"
                        "• Bot এর Admin rights আছে\n\n"
                        "আবার try করুন অথবা /cancel করুন:",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(f"❌ Error: {e}\n\nআবার try করুন অথবা /cancel করুন:")
        except ValueError:
            await update.message.reply_text(
                "❌ Channel ID অবশ্যই number হতে হবে!\n"
                "Example: `-1001234567890`\n\n"
                "আবার পাঠান অথবা /cancel করুন:"
            )
        return
    
    if state['action'] == 'rename_channel':
        new_name = text.strip()
        if not new_name:
            await update.message.reply_text("❌ Name খালি রাখা যাবে না। আবার পাঠান:")
            return
        channel_id = state['channel_id']
        try:
            force_join_col.update_one(
                {'channel_id': channel_id},
                {'$set': {'display_name': new_name}}
            )
            await update.message.reply_text(
                f"✅ **Channel Renamed!**\n\n"
                f"নতুন নাম: **{new_name}**\n\n"
                f"এখন থেকে user এর কাছে এই নামে দেখাবে।",
                parse_mode=ParseMode.MARKDOWN
            )
            del admin_states[user_id]
        except Exception as e:
            logger.error(f"Error renaming channel: {e}")
            await update.message.reply_text("❌ Rename করা যায়নি। আবার try করুন।")
        return

    if state['action'] == 'add_channel':
        parts = text.split()
        
        # Supported formats:
        # Format 1: channel_id username [display_name]           (public)
        # Format 2: channel_id invite_link [display_name]        (private)
        # Format 3: channel_id username invite_link [display_name] (private with username)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "**Public Channel:**\n`channel_id username [DisplayName]`\n\n"
                "**Private Channel:**\n`channel_id invite_link [DisplayName]`\n\n"
                "**Private + Username:**\n`channel_id username invite_link [DisplayName]`\n\n"
                "Examples:\n"
                "`-1001234567890 MyChannel Cineflix Official`\n"
                "`-1001234567890 https://t.me/+xxxxx Cineflix Private`\n"
                "`-1001234567890 MyChannel https://t.me/+xxxxx Cineflix Official`\n\n"
                "💡 DisplayName না দিলে auto-number হবে (Channel 1, Channel 2...)",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            channel_id = int(parts[0])
            invite_link = None
            display_name = None

            # Detect format
            if parts[1].startswith('https://t.me/'):
                # Format 2: channel_id invite_link [display_name]
                invite_link = parts[1]
                username = f"private_{abs(channel_id)}"
                display_name = " ".join(parts[2:]) if len(parts) > 2 else None
            elif len(parts) >= 3 and parts[2].startswith('https://t.me/'):
                # Format 3: channel_id username invite_link [display_name]
                username = parts[1].replace('@', '')
                invite_link = parts[2]
                display_name = " ".join(parts[3:]) if len(parts) > 3 else None
            else:
                # Format 1: channel_id username [display_name]
                username = parts[1].replace('@', '')
                display_name = " ".join(parts[2:]) if len(parts) > 2 else None
            
            # Validate invite link format if provided
            if invite_link and not (invite_link.startswith('https://t.me/+') or invite_link.startswith('https://t.me/joinchat/')):
                await update.message.reply_text(
                    "❌ Invalid invite link!\n\n"
                    "Private channel invite link must start with:\n"
                    "`https://t.me/+xxxxx` or `https://t.me/joinchat/xxxxx`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if add_force_join_channel(channel_id, username, invite_link, display_name):
                # Get actual display_name that was saved (in case auto-numbered)
                saved = force_join_col.find_one({'channel_id': channel_id})
                actual_name = saved.get('display_name', display_name or 'Auto') if saved else (display_name or 'Auto')
                channel_type = "🔒 Private" if invite_link else "📢 Public"
                link_info = f"\n**Invite Link:** `{invite_link}`" if invite_link else ""
                await update.message.reply_text(
                    f"✅ **Channel Added!**\n\n"
                    f"**Type:** {channel_type}\n"
                    f"**Display Name:** {actual_name}\n"
                    f"**Username:** @{username}\n"
                    f"**ID:** `{channel_id}`{link_info}\n\n"
                    f"💡 User এর কাছে **\"{actual_name}\"** দেখাবে",
                    parse_mode=ParseMode.MARKDOWN
                )
                del admin_states[user_id]
            else:
                await update.message.reply_text("❌ Failed to add channel")
        except ValueError:
            await update.message.reply_text("❌ Channel ID must be a number")
    
    # 🔥 NEW: Add Verified Channel Handler
    elif state['action'] == 'add_verified_channel':
        try:
            raw = text.strip().replace(' ', '')
            if raw.lstrip('-').isdigit():
                channel_id = int(raw)
                if channel_id > 0 and len(str(channel_id)) >= 10:
                    channel_id = int(f"-100{channel_id}")
            else:
                await update.message.reply_text(
                    "❌ **Invalid Channel ID!**\n\n"
                    "Channel ID number হতে হবে।\n"
                    "Example: `-1001234567890`\n\n"
                    "আবার পাঠান অথবা /cancel করুন:",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            channel_id = channel_id  # already set above
            
            # Check if bot is admin in this channel
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or f"Channel {channel_id}"
                
                # Verify bot is admin
                bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ **Bot is not admin in this channel!**\n\n"
                        "Please make the bot admin first, then try again.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Add to verified channels
                if add_verified_channel(channel_id, channel_name):
                    await update.message.reply_text(
                        f"✅ **Channel Verified!**\n\n"
                        f"**Name:** {channel_name}\n"
                        f"**ID:** `{channel_id}`\n\n"
                        f"Videos from this channel will now trigger notifications!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    del admin_states[user_id]
                else:
                    await update.message.reply_text("❌ Failed to add verified channel")
                    
            except BadRequest as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg:
                    await update.message.reply_text(
                        "❌ **Channel not found!**\n\n"
                        "Please check:\n"
                        "• Channel ID is correct\n"
                        "• Bot is added to the channel\n"
                        "• Bot has admin rights",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(f"❌ Error: {e}")
        except ValueError:
            await update.message.reply_text("❌ Channel ID must be a number (e.g., -1001234567890)")
    
    elif state['action'] == 'add_button':
        parts = text.split('|')
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Invalid format!\n\nUse: `Text | URL | Type`\n\n"
                "Example: `📢 Join Channel | https://t.me/MyChannel | url`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        btn_type = parts[2].strip().lower()
        
        if btn_type not in ['url', 'webapp']:
            await update.message.reply_text(
                "❌ Type must be 'url' or 'webapp'",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not btn_url.startswith('http'):
            await update.message.reply_text("❌ URL must start with http:// or https://")
            return
        
        # Convert webapp to web_app
        if btn_type == 'webapp':
            btn_type = 'web_app'
        
        location = state['location']
        existing_count = len(get_buttons(location))
        
        if add_button(location, btn_text, btn_url, btn_type, order=existing_count):
            location_name = "Welcome Message" if location == "welcome" else "After Video Message"
            await update.message.reply_text(
                f"✅ **Button Added to {location_name}!**\n\n"
                f"Text: {btn_text}\n"
                f"URL: {btn_url}\n"
                f"Type: {btn_type}",
                parse_mode=ParseMode.MARKDOWN
            )
            del admin_states[user_id]
        else:
            await update.message.reply_text("❌ Failed to add button")
    
    elif state['action'] == 'edit_message':
        msg_key = state['key']
        if set_message(msg_key, text):
            await update.message.reply_text("✅ Message updated!")
            del admin_states[user_id]
        else:
            await update.message.reply_text("❌ Failed to update message")
    
    elif state['action'] == 'edit_setting':
        # Get the actual setting key (mapped from callback data)
        setting_key = state.get('actual_key', state['key'])
        
        # Clean up input
        text = text.strip()
        
        # Type conversion and validation
        if setting_key == 'main_channel_id':
            try:
                text = int(text)
            except ValueError:
                await update.message.reply_text("❌ Channel ID must be a number")
                return
        elif setting_key == 'main_channel_username':
            # Remove @ if user added it
            text = text.replace('@', '')
        elif setting_key == 'mini_app_url':
            # Validate URL format
            if not text.startswith('http'):
                await update.message.reply_text("❌ URL must start with http:// or https://")
                return
        elif setting_key == 'video_protection':
            text = text.lower() in ['true', 'yes', '1', 'on']
        
        if set_setting(setting_key, text):
            await update.message.reply_text(
                f"✅ **{setting_key.replace('_', ' ').title()} Updated!**\n\n"
                f"New value: `{text}`",
                parse_mode=ParseMode.MARKDOWN
            )
            del admin_states[user_id]
        else:
            await update.message.reply_text("❌ Failed to update setting")

# ===================== NEW: BROADCAST HANDLER =====================

# ===================== 📢 POST MANAGER - NEW FEATURE =====================

def get_post_manager_channels():
    """সব post manager channels return করে (ON + OFF দুটোই)"""
    try:
        return list(post_manager_channels_col.find({}))
    except Exception as e:
        logger.error(f"Error getting post manager channels: {e}")
        return []

def toggle_post_manager_channel(channel_id):
    """Post Manager channel ON/OFF toggle"""
    try:
        ch = post_manager_channels_col.find_one({'channel_id': channel_id})
        if not ch:
            return None
        new_status = not ch.get('is_active', True)
        post_manager_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {'is_active': new_status}}
        )
        return new_status
    except Exception as e:
        logger.error(f"Error toggling post manager channel: {e}")
        return None

def add_post_manager_channel(channel_id, channel_name):
    try:
        post_manager_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'is_active': True,
                'added_at': datetime.utcnow()
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error adding post manager channel: {e}")
        return False

def remove_post_manager_channel(channel_id):
    try:
        result = post_manager_channels_col.delete_one({'channel_id': channel_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing post manager channel: {e}")
        return False

def is_post_manager_channel(channel_id):
    try:
        return post_manager_channels_col.find_one({'channel_id': channel_id, 'is_active': True}) is not None
    except:
        return False

def save_pending_post(channel_id, message_id, media_type, file_id=None, caption=None, text=None):
    try:
        import time
        code = f"pp_{int(time.time())}"
        pending_posts_col.insert_one({
            'code': code,
            'channel_id': channel_id,
            'message_id': message_id,
            'media_type': media_type,
            'file_id': file_id,
            'caption': caption,
            'text': text,
            'buttons': [],
            'status': 'pending',
            'created_at': datetime.utcnow()
        })
        return code
    except Exception as e:
        logger.error(f"Error saving pending post: {e}")
        return None

def get_pending_post(code):
    try:
        return pending_posts_col.find_one({'code': code, 'status': 'pending'})
    except Exception as e:
        logger.error(f"Error getting pending post: {e}")
        return None

def update_pending_post_buttons(code, buttons):
    try:
        pending_posts_col.update_one(
            {'code': code},
            {'$set': {'buttons': buttons}}
        )
        return True
    except Exception as e:
        logger.error(f"Error updating pending post buttons: {e}")
        return False

def close_pending_post(code):
    try:
        pending_posts_col.update_one({'code': code}, {'$set': {'status': 'done'}})
    except:
        pass

def build_post_buttons_keyboard(buttons, code, for_channel=True):
    """
    Build keyboard from saved buttons list.
    for_channel=True → web_app type কে url হিসেবে send করবে
    কারণ Telegram channel post এ web_app button support করে না।
    """
    keyboard = []
    for btn in buttons:
        btn_type = btn['type']
        btn_url = btn['url']
        btn_text = btn['text']
        if btn_type == 'web_app' and for_channel:
            # Channel post এ web_app চলে না — url হিসেবে পাঠাও
            keyboard.append([InlineKeyboardButton(btn_text, url=btn_url)])
        elif btn_type == 'web_app':
            keyboard.append([InlineKeyboardButton(btn_text, web_app={"url": btn_url})])
        else:
            keyboard.append([InlineKeyboardButton(btn_text, url=btn_url)])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def post_manager_channel_keyboard():
    channels = get_post_manager_channels()
    keyboard = []
    if channels:
        for ch in channels:
            ch_name = ch.get('channel_name', str(ch['channel_id']))
            ch_id = ch['channel_id']
            is_on = ch.get('is_active', True)
            toggle_icon = "🟢 ON" if is_on else "🔴 OFF"
            keyboard.append([
                InlineKeyboardButton(f"📢 {ch_name}", callback_data=f"pm_compose_{ch_id}"),
                InlineKeyboardButton(toggle_icon, callback_data=f"pm_toggle_{ch_id}"),
                InlineKeyboardButton("❌", callback_data=f"pm_remove_{ch_id}")
            ])
    else:
        keyboard.append([InlineKeyboardButton("📝 কোনো channel নেই", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("➕ Channel যোগ করুন", callback_data="pm_add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

# ===================== 📌 PINNED BUTTON - NEW FEATURE =====================

def get_pinned_buttons(channel_id):
    try:
        doc = pinned_buttons_col.find_one({'channel_id': channel_id})
        return doc.get('buttons', []) if doc else []
    except Exception as e:
        logger.error(f"Error getting pinned buttons: {e}")
        return []

def save_pinned_buttons(channel_id, buttons, channel_name=None):
    try:
        update_data = {'channel_id': channel_id, 'buttons': buttons, 'updated_at': datetime.utcnow()}
        if channel_name:
            update_data['channel_name'] = channel_name
        pinned_buttons_col.update_one(
            {'channel_id': channel_id},
            {'$set': update_data},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error saving pinned buttons: {e}")
        return False

def get_pinned_channels():
    try:
        return list(pinned_buttons_col.find({}))
    except:
        return []

def build_pinned_keyboard(buttons):
    """
    Build pinned message keyboard.
    Channel pinned message এ web_app চলে না → url হিসেবে পাঠাও।
    """
    keyboard = []
    for btn in buttons:
        btn_type = btn['type']
        if btn_type == 'web_app':
            keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        else:
            keyboard.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def pinned_manager_keyboard():
    channels = get_pinned_channels()
    keyboard = []
    if channels:
        for ch in channels:
            ch_id = ch['channel_id']
            ch_name = ch.get('channel_name', f"Channel {ch_id}")
            btns = ch.get('buttons', [])
            keyboard.append([
                InlineKeyboardButton(f"📌 {ch_name} ({len(btns)} btn)", callback_data=f"pin_manage_{ch_id}"),
                InlineKeyboardButton("🗑️", callback_data=f"pin_delete_channel_{ch_id}")
            ])
    else:
        keyboard.append([InlineKeyboardButton("📝 কোনো channel নেই", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("➕ নতুন Channel সেট করুন", callback_data="pin_add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

def pinned_channel_keyboard(channel_id, buttons):
    keyboard = []
    for i, btn in enumerate(buttons):
        icon = "🌐" if btn['type'] == 'web_app' else "🔗"
        keyboard.append([
            InlineKeyboardButton(f"{icon} {btn['text']}", callback_data="noop"),
            InlineKeyboardButton("❌", callback_data=f"pin_remove_btn_{channel_id}_{i}")
        ])
    keyboard.append([InlineKeyboardButton("➕ Button যোগ করুন", callback_data=f"pin_add_btn_{channel_id}")])
    keyboard.append([InlineKeyboardButton("📌 Pin Message এ Apply করুন", callback_data=f"pin_apply_{channel_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_pinned_btn")])
    return InlineKeyboardMarkup(keyboard)

# ===================== 📢 POST MANAGER CHANNEL POST HANDLER =====================

async def handle_post_manager_channel_post(message, context):
    """
    Post Manager channel এ post হলে admin কে forward করবে
    এবং edit/button option দেবে — Advanced UI
    """
    channel_id = message.chat.id
    message_id = message.message_id
    channel_name = message.chat.title or str(channel_id)

    media_type = 'text'
    file_id = None
    caption = message.caption
    text_content = message.text

    if message.video:
        media_type = 'video'
        file_id = message.video.file_id
    elif message.photo:
        media_type = 'photo'
        file_id = message.photo[-1].file_id
    elif message.document:
        media_type = 'document'
        file_id = message.document.file_id
    elif message.animation:
        media_type = 'animation'
        file_id = message.animation.file_id
    elif message.audio:
        media_type = 'audio'
        file_id = message.audio.file_id

    code = save_pending_post(channel_id, message_id, media_type, file_id, caption, text_content)
    if not code:
        return

    type_icons = {'video': '🎬', 'photo': '🖼️', 'text': '📝', 'document': '📄', 'animation': '🎞️', 'audio': '🎵'}
    icon = type_icons.get(media_type, '📁')

    info_text = (
        f"📢 **নতুন Post — {channel_name}**\n\n"
        f"{icon} Type: `{media_type}`\n"
        f"🕐 Time: {datetime.utcnow().strftime('%H:%M UTC')}\n\n"
        f"👇 কী করতে চান?"
    )

    action_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Button যোগ করুন", callback_data=f"pm_addbtn_{code}"),
            InlineKeyboardButton("✏️ Caption Edit", callback_data=f"pm_editcap_{code}")
        ],
        [
            InlineKeyboardButton("✅ এভাবেই রাখুন", callback_data=f"pm_postasis_{code}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"pm_delete_{code}")
        ]
    ])

    try:
        try:
            await context.bot.copy_message(
                chat_id=ADMIN_ID,
                from_chat_id=channel_id,
                message_id=message_id
            )
        except Exception:
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=channel_id,
                message_id=message_id
            )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=info_text,
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Post Manager forward error: {e}")

# ===================== 📢 POST MANAGER BUTTON PANEL HELPERS =====================

async def show_pm_button_panel(query, code):
    """Show current buttons + add/remove/apply options — Advanced UI"""
    post = get_pending_post(code)
    if not post:
        await query.answer("❌ Post পাওয়া যায়নি!", show_alert=True)
        return

    buttons = post.get('buttons', [])
    mtype = post.get('media_type', 'text')
    type_icons = {'video': '🎬', 'photo': '🖼️', 'text': '📝', 'document': '📄', 'animation': '🎞️', 'audio': '🎵'}
    icon = type_icons.get(mtype, '📁')

    text = (
        f"🔘 **Post Button Manager**\n\n"
        f"{icon} Post Type: `{mtype}`\n"
        f"🔢 Buttons: **{len(buttons)}টি**\n\n"
    )

    keyboard = []
    for i, btn in enumerate(buttons):
        icon_btn = "🌐" if btn['type'] == 'web_app' else "🔗"
        keyboard.append([
            InlineKeyboardButton(f"{icon_btn} {btn['text']}", callback_data="noop"),
            InlineKeyboardButton("❌", callback_data=f"pm_rmbtn_{code}_{i}")
        ])

    keyboard.append([InlineKeyboardButton("➕ আরো Button যোগ করুন", callback_data=f"pm_addbtn_{code}")])
    if buttons:
        keyboard.append([InlineKeyboardButton("✅ Channel Post এ Apply করুন", callback_data=f"pm_apply_{code}")])
        text += "👇 বর্তমান buttons — ❌ চেপে remove করুন:"
    else:
        text += "👇 এখনো কোনো button নেই। যোগ করুন:"
    keyboard.append([InlineKeyboardButton("🗑️ Post বাতিল করুন", callback_data=f"pm_delete_{code}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# ===================== 📢 POST MANAGER CALLBACKS =====================

async def handle_pm_callbacks(data, query, context, user_id):
    """Handle all post manager callbacks"""

    # --- COMPOSE FROM BOT ---
    if data.startswith("pm_compose_"):
        ch_id = int(data.replace("pm_compose_", ""))
        channels = get_post_manager_channels()
        ch = next((c for c in channels if c['channel_id'] == ch_id), None)
        ch_name = ch.get('channel_name', str(ch_id)) if ch else str(ch_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Text Post", callback_data=f"pm_ctype_text_{ch_id}")],
            [InlineKeyboardButton("🖼️ Photo + Caption", callback_data=f"pm_ctype_photo_{ch_id}")],
            [InlineKeyboardButton("🎬 Video + Caption", callback_data=f"pm_ctype_video_{ch_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_post_manager")]
        ])
        await query.edit_message_text(
            f"📢 **{ch_name}** — নতুন Post তৈরি করুন\n\nPost type বেছে নিন:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("pm_ctype_"):
        rest = data.replace("pm_ctype_", "")
        parts = rest.split("_", 1)
        ctype = parts[0]
        ch_id = int(parts[1])
        channels = get_post_manager_channels()
        ch = next((c for c in channels if c['channel_id'] == ch_id), None)
        ch_name = ch.get('channel_name', str(ch_id)) if ch else str(ch_id)
        admin_states[user_id] = {'action': f'pm_compose_{ctype}', 'channel_id': ch_id, 'channel_name': ch_name}
        if ctype == 'text':
            await query.message.reply_text(
                f"📝 **{ch_name}** — Text Post\n\nPost এর text পাঠান:\n\n/cancel করতে লিখুন /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
        elif ctype == 'photo':
            await query.message.reply_text(
                f"🖼️ **{ch_name}** — Photo Post\n\nPhoto পাঠান (caption optional — photo এর সাথেই দিন):\n\n/cancel করতে লিখুন /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
        elif ctype == 'video':
            await query.message.reply_text(
                f"🎬 **{ch_name}** — Video Post\n\nVideo পাঠান (caption optional — video এর সাথেই দিন):\n\n/cancel করতে লিখুন /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # ADD BUTTON to composed post (before sending)
    if data.startswith("pm_addbtn_composed_"):
        code = data.replace("pm_addbtn_composed_", "")
        admin_states[user_id] = {'action': 'pm_add_composed_button', 'code': code}
        await query.message.reply_text(
            f"➕ **Button যোগ করুন**\n\n`বাটনের নাম | লিঙ্ক | type`\n\n"
            f"type: `url` বা `webapp`\n\nExample:\n`🎮 Open App | https://myapp.com | webapp`\n\n/cancel করতে লিখুন /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # SEND composed post
    if data.startswith("pm_send_composed_"):
        code = data.replace("pm_send_composed_", "")
        post = get_pending_post(code)
        if not post:
            await query.answer("❌ Post পাওয়া যায়নি!", show_alert=True)
            return
        buttons = post.get('buttons', [])
        ch_id = post['channel_id']
        reply_markup = build_post_buttons_keyboard(buttons, code, for_channel=True) if buttons else None
        try:
            mtype = post.get('media_type', 'text')
            file_id = post.get('file_id')
            caption = post.get('caption') or post.get('text') or ''
            if mtype == 'text':
                await context.bot.send_message(chat_id=ch_id, text=caption, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            elif mtype == 'photo':
                await context.bot.send_photo(chat_id=ch_id, photo=file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            elif mtype == 'video':
                await context.bot.send_video(chat_id=ch_id, video=file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            close_pending_post(code)
            await query.edit_message_text("✅ **Post channel এ পাঠানো হয়েছে!**", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(f"❌ Error!\n\n`{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        return

    # --- ADD BUTTON ---
    if data.startswith("pm_addbtn_"):
        code = data.replace("pm_addbtn_", "")
        admin_states[user_id] = {'action': 'pm_add_button', 'code': code}
        await query.message.reply_text(
            f"➕ **Button যোগ করুন**\n\n"
            f"নিচের format এ পাঠান:\n"
            f"`বাটনের নাম | লিঙ্ক | type`\n\n"
            f"**type:**\n"
            f"• `url` → সাধারণ লিঙ্ক\n"
            f"• `webapp` → Mini App\n\n"
            f"**Examples:**\n"
            f"`📢 Join Channel | https://t.me/mychannel | url`\n"
            f"`🎮 Open App | https://myapp.com | webapp`\n"
            f"`🔗 Watch Now | https://t.me/mychannel/123 | url`\n\n"
            f"যতটা খুশি button দিতে পারবেন। শেষ হলে Apply করুন।\n\n"
            f"/cancel করতে লিখুন /cancel",
            parse_mode=ParseMode.MARKDOWN
        )

    # --- REMOVE BUTTON ---
    elif data.startswith("pm_rmbtn_"):
        parts = data.replace("pm_rmbtn_", "").rsplit("_", 1)
        code, idx = parts[0], int(parts[1])
        post = get_pending_post(code)
        if post:
            buttons = post.get('buttons', [])
            if 0 <= idx < len(buttons):
                buttons.pop(idx)
                update_pending_post_buttons(code, buttons)
                await query.answer("✅ Button remove হয়েছে!")
            await show_pm_button_panel(query, code)

    # --- APPLY BUTTONS TO POST ---
    elif data.startswith("pm_apply_"):
        code = data.replace("pm_apply_", "")
        post = get_pending_post(code)
        if not post:
            await query.answer("❌ Post পাওয়া যায়নি!", show_alert=True)
            return
        buttons = post.get('buttons', [])
        channel_id = post['channel_id']
        message_id = post['message_id']

        reply_markup = build_post_buttons_keyboard(buttons, code, for_channel=True) if buttons else None

        try:
            await context.bot.edit_message_reply_markup(
                chat_id=channel_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            close_pending_post(code)
            await query.edit_message_text(
                f"✅ **Buttons Apply হয়েছে!**\n\n"
                f"{len(buttons)}টি button channel post এ লাগানো হয়েছে।",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Error!**\n\n`{str(e)[:200]}`\n\n"
                f"নিশ্চিত করুন Bot সেই channel এর Admin এবং Post Edit permission আছে।",
                parse_mode=ParseMode.MARKDOWN
            )

    # --- POST AS IS (no buttons) ---
    elif data.startswith("pm_postasis_"):
        code = data.replace("pm_postasis_", "")
        post = get_pending_post(code)
        if not post:
            await query.answer("❌ Post পাওয়া যায়নি!", show_alert=True)
            return
        close_pending_post(code)
        await query.edit_message_text("✅ Post যেমন আছে তেমনই থাকবে।", parse_mode=ParseMode.MARKDOWN)

    # --- DELETE POST ---
    elif data.startswith("pm_delete_"):
        code = data.replace("pm_delete_", "")
        post = get_pending_post(code)
        if not post:
            await query.answer("❌ Post পাওয়া যায়নি!", show_alert=True)
            return
        try:
            if post.get('message_id'):
                await context.bot.delete_message(
                    chat_id=post['channel_id'],
                    message_id=post['message_id']
                )
            close_pending_post(code)
            await query.edit_message_text("🗑️ **Post delete করা হয়েছে।**", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            close_pending_post(code)
            await query.edit_message_text("🗑️ **Post বাতিল করা হয়েছে।**", parse_mode=ParseMode.MARKDOWN)

    # --- EDIT CAPTION ---
    elif data.startswith("pm_editcap_"):
        code = data.replace("pm_editcap_", "")
        admin_states[user_id] = {'action': 'pm_edit_caption', 'code': code}
        await query.message.reply_text(
            f"✏️ **Caption/Text Edit করুন**\n\n"
            f"নতুন caption বা text পাঠান।\n"
            f"Telegram markdown ব্যবহার করতে পারবেন।\n\n"
            f"/cancel করতে লিখুন /cancel",
            parse_mode=ParseMode.MARKDOWN
        )

    # --- TOGGLE ON/OFF ---
    elif data.startswith("pm_toggle_"):
        ch_id = int(data.replace("pm_toggle_", ""))
        new_status = toggle_post_manager_channel(ch_id)
        if new_status is None:
            await query.answer("❌ Toggle করা যায়নি!", show_alert=True)
        else:
            status_text = "🟢 ON" if new_status else "🔴 OFF"
            await query.answer(f"✅ Post Manager: {status_text}")
        pm_text = (
            "📢 **Post Manager**\n\n"
            "🟢 ON — channel এ post হলে admin কে আসবে\n"
            "🔴 OFF — কিছুই হবে না, admin কে disturb করবে না\n\n"
            "Channel বেছে নিন:"
        )
        await query.edit_message_text(pm_text, reply_markup=post_manager_channel_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # --- REMOVE CHANNEL ---
    elif data.startswith("pm_remove_"):
        ch_id = int(data.replace("pm_remove_", ""))
        if remove_post_manager_channel(ch_id):
            await query.answer("✅ Channel remove হয়েছে!")
        else:
            await query.answer("❌ Remove করা যায়নি!", show_alert=True)
        pm_text = (
            "📢 **Post Manager**\n\n"
            "🟢 ON — channel এ post হলে admin কে আসবে\n"
            "🔴 OFF — কিছুই হবে না, admin কে disturb করবে না\n\n"
            "Channel বেছে নিন:"
        )
        await query.edit_message_text(pm_text, reply_markup=post_manager_channel_keyboard(), parse_mode=ParseMode.MARKDOWN)

    # --- ADD CHANNEL ---
    elif data == "pm_add_channel":
        admin_states[user_id] = {'action': 'add_post_manager_channel'}
        await query.message.reply_text(
            "📢 **Post Manager Channel যোগ করুন**\n\n"
            "যে channel এর posts manage করতে চান সেই channel এর **ID** পাঠান।\n\n"
            "⚠️ **শর্ত:** Bot কে সেই channel এর Admin করতে হবে\n\n"
            "**Format:** `-1001234567890`\n\n"
            "ID পাঠান অথবা /cancel করুন:",
            parse_mode=ParseMode.MARKDOWN
        )

# ===================== 📌 PINNED BUTTON CALLBACKS =====================

async def handle_pinned_callbacks(data, query, context, user_id):
    """Handle all pinned button callbacks"""

    if data == "pin_add_channel":
        admin_states[user_id] = {'action': 'add_pinned_channel'}
        await query.message.reply_text(
            "📌 **Pinned Button Channel যোগ করুন**\n\n"
            "Channel এর **ID** পাঠান:\n\n"
            "**Format:** `-1001234567890`\n\n"
            "/cancel করতে লিখুন /cancel",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("pin_manage_"):
        ch_id = int(data.replace("pin_manage_", ""))
        buttons = get_pinned_buttons(ch_id)
        channels = get_pinned_channels()
        ch = next((c for c in channels if c['channel_id'] == ch_id), None)
        ch_name = ch.get('channel_name', f"Channel {ch_id}") if ch else f"Channel {ch_id}"
        text = (
            f"📌 **Pinned Button — {ch_name}**\n\n"
            f"🔢 Buttons: **{len(buttons)}টি**\n\n"
            f"👇 নিচে buttons দেখুন ও manage করুন:\n"
            f"Apply চাপলে channel এর pinned message এ লাগবে।"
        )
        await query.edit_message_text(text, reply_markup=pinned_channel_keyboard(ch_id, buttons), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("pin_add_btn_"):
        ch_id = int(data.replace("pin_add_btn_", ""))
        admin_states[user_id] = {'action': 'add_pinned_button', 'channel_id': ch_id}
        await query.message.reply_text(
            f"➕ **Pinned Button যোগ করুন**\n\n"
            f"Format:\n`বাটনের নাম | লিঙ্ক | type`\n\n"
            f"**type:**\n"
            f"• `url` → সাধারণ লিঙ্ক\n"
            f"• `webapp` → Mini App\n\n"
            f"**Examples:**\n"
            f"`♻️ BACKUP | https://t.me/mychannel | url`\n"
            f"`🎮 Open App | https://myapp.com | webapp`\n\n"
            f"/cancel করতে লিখুন /cancel",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("pin_remove_btn_"):
        parts = data.replace("pin_remove_btn_", "").rsplit("_", 1)
        ch_id = int(parts[0])
        idx = int(parts[1])
        buttons = get_pinned_buttons(ch_id)
        if 0 <= idx < len(buttons):
            buttons.pop(idx)
            save_pinned_buttons(ch_id, buttons)
            await query.answer("✅ Button remove হয়েছে!")
        await query.edit_message_text(
            f"📌 **Pinned Button Manager**\n\nChannel ID: `{ch_id}`\nButtons: {len(buttons)}টি",
            reply_markup=pinned_channel_keyboard(ch_id, buttons),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data.startswith("pin_apply_"):
        ch_id = int(data.replace("pin_apply_", ""))
        buttons = get_pinned_buttons(ch_id)
        if not buttons:
            await query.answer("❌ আগে Button যোগ করুন!", show_alert=True)
            return

        reply_markup = build_pinned_keyboard(buttons)

        # Try to get pinned message
        try:
            chat = await context.bot.get_chat(ch_id)
            pinned = chat.pinned_message
            if not pinned:
                await query.edit_message_text(
                    "❌ **Pinned message পাওয়া যায়নি!**\n\n"
                    "প্রথমে channel এ একটা message pin করুন।",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            await context.bot.edit_message_reply_markup(
                chat_id=ch_id,
                message_id=pinned.message_id,
                reply_markup=reply_markup
            )
            await query.edit_message_text(
                f"✅ **Pinned Message এ Buttons Apply হয়েছে!**\n\n"
                f"{len(buttons)}টি button pinned message এ লাগানো হয়েছে।\n"
                f"সব user সবসময় দেখতে পাবে ✅",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Error!**\n\n`{str(e)[:200]}`\n\n"
                f"নিশ্চিত করুন Bot সেই channel এর Admin এবং Edit permission আছে।",
                parse_mode=ParseMode.MARKDOWN
            )

    elif data.startswith("pin_delete_channel_"):
        ch_id = int(data.replace("pin_delete_channel_", ""))
        try:
            pinned_buttons_col.delete_one({'channel_id': ch_id})
            await query.answer("✅ Channel remove হয়েছে!")
        except:
            await query.answer("❌ Remove করা যায়নি!", show_alert=True)
        await query.edit_message_text(
            "📌 **Pinned Button Manager**",
            reply_markup=pinned_manager_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

# ===================== 🎙️ VOICE MANAGER - NEW FEATURE =====================

def get_voice_channels():
    """Get all voice manager channels"""
    try:
        return list(voice_channels_col.find({'is_active': True}))
    except Exception as e:
        logger.error(f"Error getting voice channels: {e}")
        return []

def add_voice_channel(channel_id, channel_name):
    """Add a voice channel"""
    try:
        voice_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'is_active': True,
                'added_at': datetime.utcnow()
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error adding voice channel: {e}")
        return False

def remove_voice_channel(channel_id):
    """Remove a voice channel"""
    try:
        result = voice_channels_col.delete_one({'channel_id': channel_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing voice channel: {e}")
        return False

def get_active_voice_channel():
    """Get the currently active/selected voice channel"""
    try:
        ch = voice_channels_col.find_one({'is_active': True, 'selected': True})
        if not ch:
            ch = voice_channels_col.find_one({'is_active': True})
        return ch
    except Exception as e:
        logger.error(f"Error getting active voice channel: {e}")
        return None

def set_selected_voice_channel(channel_id):
    """Set a channel as selected for voice uploads"""
    try:
        voice_channels_col.update_many({}, {'$unset': {'selected': ''}})
        voice_channels_col.update_one(
            {'channel_id': channel_id},
            {'$set': {'selected': True}}
        )
        return True
    except Exception as e:
        logger.error(f"Error setting selected voice channel: {e}")
        return False

def voice_manager_keyboard():
    """Voice Manager main keyboard"""
    channels = get_voice_channels()
    keyboard = []

    if channels:
        for ch in channels:
            ch_name = ch.get('channel_name', str(ch['channel_id']))
            ch_id = ch['channel_id']
            selected = '✅ ' if ch.get('selected') else '📢 '
            keyboard.append([
                InlineKeyboardButton(
                    f"{selected}{ch_name}",
                    callback_data=f"voice_select_{ch_id}"
                ),
                InlineKeyboardButton(
                    "❌",
                    callback_data=f"voice_remove_{ch_id}"
                )
            ])
    else:
        keyboard.append([InlineKeyboardButton("📝 কোনো channel নেই", callback_data="noop")])

    keyboard.append([InlineKeyboardButton("➕ Channel যোগ করুন", callback_data="voice_add_channel")])
    keyboard.append([InlineKeyboardButton("🎙️ Voice পাঠান (Audio দিন)", callback_data="voice_send_now")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

def _check_ffmpeg_available():
    """Check if ffmpeg is installed and accessible"""
    import shutil
    return shutil.which('ffmpeg') is not None

async def handle_voice_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎙️ VOICE MANAGER: Admin audio file পাঠালে voice message হিসেবে channel এ post করবে
    State: admin_states[user_id]['action'] == 'voice_upload'
    ffmpeg থাকলে → OGG Opus convert করে send_voice (রেকর্ড করা ভয়েসের মতো দেখায়)
    ffmpeg না থাকলে → audio file হিসেবে send করবে (কিন্তু কাজ করবে)
    """
    import tempfile
    import subprocess

    user_id = update.effective_user.id
    message = update.message

    if user_id != ADMIN_ID:
        return

    state = admin_states.get(user_id, {})
    if state.get('action') != 'voice_upload':
        return

    target_channel = get_active_voice_channel()
    if not target_channel:
        await message.reply_text(
            "❌ **কোনো Voice Channel সেট করা নেই!**\n\n"
            "Admin Panel → 🎙️ Voice Manager → Channel যোগ করুন",
            parse_mode=ParseMode.MARKDOWN
        )
        del admin_states[user_id]
        return

    channel_id = target_channel['channel_id']
    channel_name = target_channel.get('channel_name', str(channel_id))

    # Detect audio file
    audio_file = None
    file_ext = 'mp3'
    is_already_voice = False

    if message.voice:
        # Already a voice message — send directly, no conversion needed
        audio_file = message.voice
        file_ext = 'ogg'
        is_already_voice = True
    elif message.audio:
        audio_file = message.audio
        mime = message.audio.mime_type or ''
        if 'ogg' in mime:
            file_ext = 'ogg'
        elif 'mp4' in mime or 'm4a' in mime:
            file_ext = 'm4a'
        elif 'wav' in mime:
            file_ext = 'wav'
        else:
            file_ext = 'mp3'
    elif message.document and message.document.mime_type and 'audio' in message.document.mime_type:
        audio_file = message.document
        file_name = message.document.file_name or 'audio.mp3'
        file_ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else 'mp3'
    else:
        await message.reply_text(
            "❌ **Audio ফাইল পাঠান!**\n\nMP3, WAV, OGG, M4A যেকোনো format চলবে।",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    processing_msg = await message.reply_text("⏳ **Processing... একটু অপেক্ষা করুন**", parse_mode=ParseMode.MARKDOWN)
    ffmpeg_available = _check_ffmpeg_available()

    try:
        tg_file = await context.bot.get_file(audio_file.file_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, f"input.{file_ext}")
            output_path = os.path.join(tmpdir, "output.ogg")
            await tg_file.download_to_drive(input_path)

            sent = None

            # Case 1: Already a voice message → send directly
            if is_already_voice:
                with open(input_path, 'rb') as vf:
                    sent = await context.bot.send_voice(chat_id=channel_id, voice=vf)

            # Case 2: ffmpeg available → convert to OGG Opus → send_voice (looks like recorded voice)
            elif ffmpeg_available:
                result = subprocess.run(
                    ['ffmpeg', '-i', input_path, '-c:a', 'libopus', '-b:a', '64k',
                     '-ar', '48000', '-ac', '1', '-y', output_path],
                    capture_output=True, timeout=120
                )
                if result.returncode == 0:
                    with open(output_path, 'rb') as vf:
                        sent = await context.bot.send_voice(chat_id=channel_id, voice=vf)
                    logger.info("✅ Voice converted and sent via ffmpeg")
                else:
                    # ffmpeg failed even though available — send as audio
                    logger.warning(f"ffmpeg failed: {result.stderr.decode()[:200]}")
                    with open(input_path, 'rb') as af:
                        sent = await context.bot.send_audio(chat_id=channel_id, audio=af)

            # Case 3: ffmpeg NOT available → send as audio file (fallback)
            else:
                logger.warning("⚠️ ffmpeg not found — sending as audio file instead of voice")
                with open(input_path, 'rb') as af:
                    sent = await context.bot.send_audio(chat_id=channel_id, audio=af)

        try:
            await processing_msg.delete()
        except:
            pass

        if ffmpeg_available or is_already_voice:
            success_text = (
                f"✅ **Voice Message পাঠানো হয়েছে!**\n\n"
                f"📢 Channel: **{channel_name}**\n"
                f"🎙️ রেকর্ড করা ভয়েসের মতো দেখাবে ✅"
            )
        else:
            success_text = (
                f"✅ **Audio পাঠানো হয়েছে!**\n\n"
                f"📢 Channel: **{channel_name}**\n"
                f"⚠️ ffmpeg নেই, তাই audio file হিসেবে গেছে।\n"
                f"Voice message চাইলে Railway এ nixpacks.toml এ ffmpeg যোগ করুন।"
            )

        await message.reply_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎙️ Voice Manager", callback_data="admin_voice_manager")
            ]])
        )
        logger.info(f"✅ Audio/Voice sent to channel {channel_id}, ffmpeg={ffmpeg_available}")

    except subprocess.TimeoutExpired:
        try:
            await processing_msg.edit_text("❌ Timeout! ফাইল অনেক বড়, ছোট ফাইল দিন।")
        except:
            pass
    except Exception as e:
        logger.error(f"Voice upload error: {e}", exc_info=True)
        err_msg = str(e)[:150]
        try:
            await processing_msg.edit_text(f"❌ Error!\n\n`{err_msg}`", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.reply_text(f"❌ Error!\n\n`{err_msg}`", parse_mode=ParseMode.MARKDOWN)

    if user_id in admin_states:
        del admin_states[user_id]



# ===================== 🔥 ADMIN DIRECT UPLOAD HANDLER =====================
async def handle_admin_direct_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when admin sends video directly to bot"""
    user_id = update.effective_user.id
    message = update.message
    
    # Detect media type and get file_id
    file_id = None
    file_unique_id = None
    media_type = None
    file_name = "Untitled"
    
    if message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        media_type = 'video'
        file_name = message.video.file_name or "Video"
    elif message.document:
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
        media_type = 'document'
        file_name = message.document.file_name or "Document"
    elif message.animation:
        file_id = message.animation.file_id
        file_unique_id = message.animation.file_unique_id
        media_type = 'animation'
        file_name = "Animation"
    
    if not file_id:
        return
    
    # Use caption as title if provided
    title = message.caption or file_name
    
    # Save to database
    code = save_direct_video(file_id, file_unique_id, title, media_type)
    
    if not code:
        await message.reply_text("❌ Failed to save video. Please try again.")
        return
    
    # Get bot username for deep link
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    
    # Create deep link
    deep_link = f"https://t.me/{bot_username}?start={code}"
    
    # Send info to admin
    info_text = f"""✅ <b>Video Saved Successfully!</b>

📁 Title: {html.escape(title)}
🎬 Type: {media_type.upper()}
🔑 Code: <code>{code}</code>

🌐 <b>Deep Link:</b>
{deep_link}

👇 <b>Copy this code for Mini App:</b>"""
    
    await message.reply_text(
        info_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    
    # Send copyable code separately
    await message.reply_text(
        f"<code>{code}</code>",
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"✅ Admin direct upload: code={code}, type={media_type}, title={title}")
    
    # 🔥 Auto-forward to ALL enabled forward channels
    fwd_channels = get_forward_channels()
    enabled_channels = [ch for ch in fwd_channels if ch.get('enabled', True)]
    if enabled_channels:
        success_list = []
        fail_list = []
        for fwd_ch in enabled_channels:
            fwd_ch_id = fwd_ch['channel_id']
            fwd_ch_name = fwd_ch.get('channel_name', str(fwd_ch_id))
            try:
                caption_text = f"🎬 {title}\n\n🔗 Deep Link: {deep_link}"
                if media_type == 'video':
                    await context.bot.send_video(chat_id=fwd_ch_id, video=file_id, caption=caption_text)
                elif media_type == 'document':
                    await context.bot.send_document(chat_id=fwd_ch_id, document=file_id, caption=caption_text)
                elif media_type == 'animation':
                    await context.bot.send_animation(chat_id=fwd_ch_id, animation=file_id, caption=caption_text)
                success_list.append(fwd_ch_name)
                logger.info(f"✅ Forwarded to {fwd_ch_name} ({fwd_ch_id})")
            except Exception as e:
                fail_list.append(fwd_ch_name)
                logger.error(f"❌ Failed to forward to {fwd_ch_id}: {e}")
        
        # শুধু তখনই message দেবে যখন কিছু সফল বা ব্যর্থ হয়েছে
        if success_list or fail_list:
            result_text = "📤 **Forward সম্পন্ন!**\n\n"
            if success_list:
                result_text += f"✅ সফল ({len(success_list)}টি):\n" + "\n".join([f"  • {n}" for n in success_list]) + "\n\n"
            if fail_list:
                result_text += f"❌ ব্যর্থ ({len(fail_list)}টি):\n" + "\n".join([f"  • {n}" for n in fail_list])
            await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message from admin"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        return
    
    # Get all users
    all_users = get_all_users()
    
    if not all_users:
        await update.message.reply_text("❌ No users to broadcast to!")
        del admin_states[user_id]
        return
    
    # Confirm broadcast
    await update.message.reply_text(
        f"📢 **Broadcasting to {len(all_users)} users...**\n\n"
        f"This may take a few moments. Please wait...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success_count = 0
    fail_count = 0
    
    # Forward the message to all users
    for target_user_id in all_users:
        try:
            # Copy the message to each user
            if update.message.photo:
                # Photo message
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption,
                    parse_mode=ParseMode.MARKDOWN if update.message.caption else None
                )
            elif update.message.video:
                # Video message
                await context.bot.send_video(
                    chat_id=target_user_id,
                    video=update.message.video.file_id,
                    caption=update.message.caption,
                    parse_mode=ParseMode.MARKDOWN if update.message.caption else None
                )
            else:
                # Text message
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=update.message.text,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            success_count += 1
            logger.info(f"✅ Broadcast sent to user {target_user_id}")
            
            # Rate limit: avoid Telegram flood (30 msgs/sec max)
            if success_count % 25 == 0:
                await asyncio.sleep(1)
            
        except Exception as e:
            fail_count += 1
            logger.error(f"❌ Failed to send broadcast to user {target_user_id}: {e}")
    
    # Send summary to admin
    await update.message.reply_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"✅ Sent: {success_count}\n"
        f"❌ Failed: {fail_count}\n"
        f"📊 Total: {len(all_users)}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Clear admin state
    del admin_states[user_id]
    
    logger.info(f"📢 Broadcast completed: {success_count} success, {fail_count} failed")


# ===================== 🔥 DIRECT VIDEO CALLBACK HELPER =====================

# ===================== ADMIN COMMANDS =====================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    stats = get_stats()
    text = f"""🔧 **CINEFLIX ADMIN PANEL**

📊 **Statistics:**
👥 Total Users: {stats['users']}
🔥 Active Today: {stats['active_today']}
📹 Videos: {stats['videos']}
👁️ Top Views: {stats['top_views']}
🔒 Force Join: {stats['force_join']}
✅ Verified Channels: {stats['verified_channels']}

Select an option below:"""
    
    await update.message.reply_text(
        text,
        reply_markup=admin_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    await update.message.reply_text(
        get_message('help'),
        parse_mode=ParseMode.MARKDOWN
    )

# ===================== ERROR HANDLER =====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors with full traceback"""
    import traceback
    
    logger.error(f"Update {update} caused error {context.error}")
    logger.error(f"Full traceback:\n{traceback.format_exc()}")

# ===================== MAIN FUNCTION =====================
def main():
    """Start the bot"""
    logger.info("🚀 Starting CINEFLIX Ultimate Bot...")
    
    # Initialize defaults
    initialize_defaults()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # ✅ NEW: Chat join request handler - CRITICAL for private channels!
    application.add_handler(ChatJoinRequestHandler(handle_chat_join_request))
    
    # ✅ Channel post handler — MUST be FIRST before private handlers
    application.add_handler(MessageHandler(
        filters.ChatType.CHANNEL,
        channel_post
    ))
    
    # ✅ Private message handlers — ChatType.PRIVATE ensures channel posts never reach here
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        admin_message_handler
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.ANIMATION | filters.VIDEO) & filters.User(ADMIN_ID),
        admin_message_handler
    ))
    # 🎙️ VOICE MANAGER: Audio handler for admin
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.AUDIO | filters.VOICE | filters.Document.AUDIO) & filters.User(ADMIN_ID),
        admin_message_handler
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("✅ CINEFLIX Ultimate Bot is running!")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"💾 MongoDB: Connected")
    logger.info(f"🎬 Ready to serve!")
    logger.info(f"✨ NEW FEATURES: Photo Support, Welcome Media, Auto Cleanup, Broadcast, Enhanced Stats, Auto-Reply")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
