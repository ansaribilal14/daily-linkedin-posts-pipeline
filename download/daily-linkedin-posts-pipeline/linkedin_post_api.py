"""
LinkedIn API Post Publisher

Posts carousel slides as a multi-image post on LinkedIn using the official API.
No cookies, no browser automation — pure API calls.

Prerequisites:
  - Run `python3 linkedin_api.py --setup --client-id ID --client-secret SECRET` first
  
Usage:
  # Post carousel slides as multi-image post
  python3 linkedin_post_api.py --carousel --date 2026-07-03

  # Post with custom caption
  python3 linkedin_post_api.py --carousel --date 2026-07-03 --caption "Custom text"

  # Post text only
  python3 linkedin_post_api.py --text "Your post text here"

  # Schedule for later (ISO datetime)
  python3 linkedin_post_api.py --carousel --date 2026-07-03 --schedule "2026-07-04T10:00:00+05:30"
"""

import os, sys, json, time, glob, argparse, base64, mimetypes
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip install requests --break-system-packages -q")
    import requests

BASE = os.path.dirname(os.path.abspath(__file__))


def load_tokens():
    token_file = os.path.join(BASE, "linkedin_tokens.json")
    if os.path.exists(token_file):
        with open(token_file) as f:
            return json.load(f)
    return None


def get_valid_token():
    """Get valid access token, refresh if needed."""
    tokens = load_tokens()
    if not tokens:
        return None, "No tokens. Run: python3 linkedin_api.py --setup --client-id ID --client-secret SECRET"
    
    if time.time() > (tokens.get("expires_at", 0) - 300):
        print("Refreshing token...")
        resp = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type": "refresh_token",
            "refresh_token": tokens.get("refresh_token", ""),
            "client_id": tokens.get("client_id", ""),
            "client_secret": tokens.get("client_secret", ""),
        })
        if resp.status_code != 200:
            return None, f"Token refresh failed: {resp.text}"
        data = resp.json()
        tokens["access_token"] = data["access_token"]
        tokens["expires_at"] = time.time() + data.get("expires_in", 5184000)
        if "refresh_token" in data:
            tokens["refresh_token"] = data["refresh_token"]
        with open(os.path.join(BASE, "linkedin_tokens.json"), "w") as f:
            json.dump(tokens, f, indent=2)
        print("Token refreshed.")
    
    return tokens["access_token"], None


def get_person_urn(access_token):
    """Get the authenticated user's person URN."""
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if resp.status_code != 200:
        return None, f"Profile lookup failed: {resp.text}"
    data = resp.json()
    return data.get("sub", ""), None


def register_image_upload(access_token, person_urn):
    """Register an image upload and get the upload URL + asset URN."""
    resp = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{person_urn}",
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
    )
    
    if resp.status_code != 200:
        return None, None, f"Register upload failed: {resp.status_code} - {resp.text}"
    
    data = resp.json()
    upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn = data["value"]["asset"]
    return upload_url, asset_urn, None


def upload_image_to_url(upload_url, image_path):
    """Upload image binary to the LinkedIn upload URL."""
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    
    resp = requests.put(
        upload_url,
        headers={"Content-Type": mime_type},
        data=image_data
    )
    
    if resp.status_code not in (200, 201):
        return f"Image upload failed: {resp.status_code} - {resp.text[:200]}"
    return None


def create_multi_image_post(access_token, person_urn, caption, asset_urns, schedule_time=None):
    """Create a LinkedIn post with multiple images (carousel)."""
    media_items = []
    for urn in asset_urns:
        media_items.append({
            "status": "READY",
            "media": urn,
            "title": {"text": "Carousel Slide"}
        })
    
    post_body = {
        "author": f"urn:li:person:{person_urn}",
        "commentary": caption,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "content": {
            "media": {
                "title": "AI Tools Carousel",
                "id": "urn:li:image:" + ",".join([urn.split(":")[-1] for urn in asset_urns]),
                "mediaList": media_items
            }
        },
        "lifecycleState": "PUBLISHED"
    }
    
    if schedule_time:
        post_body["lifecycleState"] = "DRAFT"
    
    # LinkedIn API v2 for UGC posts
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=post_body
    )
    
    if resp.status_code in (200, 201):
        post_urn = resp.headers.get("X-Restli-Id", resp.json().get("id", "unknown"))
        return post_urn, None
    else:
        return None, f"Post creation failed: {resp.status_code} - {resp.text}"


def create_text_post(access_token, person_urn, text):
    """Create a simple text post on LinkedIn."""
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json={
            "author": f"urn:li:person:{person_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    )
    
    if resp.status_code in (200, 201):
        post_urn = resp.headers.get("X-Restli-Id", "")
        return post_urn, None
    else:
        return None, f"Post failed: {resp.status_code} - {resp.text}"


def post_carousel(date_str, caption_override=None, schedule_time=None):
    """Post a carousel (multi-image) to LinkedIn."""
    # Get valid token
    access_token, err = get_valid_token()
    if err:
        print(f"❌ {err}")
        return False
    
    # Get person URN
    person_urn, err = get_person_urn(access_token)
    if err:
        print(f"❌ {err}")
        return False
    print(f"Posting as: urn:li:person:{person_urn}")
    
    # Find slides
    slides_dir = os.path.join(BASE, "carousel-routine", "output", date_str, "carousel-branded")
    slides = sorted(glob.glob(os.path.join(slides_dir, "slide-*.png")))
    
    if not slides:
        print(f"❌ No slide PNGs found in {slides_dir}")
        return False
    
    print(f"Found {len(slides)} slides to upload.")
    
    # Read caption
    if caption_override:
        caption = caption_override
    else:
        caption_path = os.path.join(BASE, "carousel_caption.txt")
        if os.path.exists(caption_path):
            with open(caption_path) as f:
                caption = f.read().strip()
        else:
            caption = ""
    
    # Upload each slide
    asset_urns = []
    for i, slide_path in enumerate(slides):
        print(f"  Uploading slide {i+1}/{len(slides)}: {os.path.basename(slide_path)}")
        
        upload_url, asset_urn, err = register_image_upload(access_token, person_urn)
        if err:
            print(f"  ❌ {err}")
            continue
        
        upload_err = upload_image_to_url(upload_url, slide_path)
        if upload_err:
            print(f"  ❌ {upload_err}")
            continue
        
        # Small delay between uploads
        time.sleep(1)
        asset_urns.append(asset_urn)
        print(f"  ✅ Uploaded → {asset_urn}")
    
    if not asset_urns:
        print("❌ No images uploaded successfully.")
        return False
    
    # Create the post
    print(f"\nCreating post with {len(asset_urns)} images...")
    post_urn, err = create_multi_image_post(access_token, person_urn, caption, asset_urns, schedule_time)
    
    if err:
        print(f"❌ {err}")
        return False
    
    print(f"\n✅ Carousel posted successfully!")
    print(f"   Post URN: {post_urn}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post to LinkedIn via API")
    parser.add_argument("--carousel", action="store_true", help="Post carousel slides")
    parser.add_argument("--date", default="", help="Date (YYYY-MM-DD)")
    parser.add_argument("--caption", default="", help="Custom caption")
    parser.add_argument("--text", help="Post text only")
    parser.add_argument("--schedule", default="", help="Schedule time (ISO 8601)")
    
    args = parser.parse_args()
    
    if args.carousel:
        date_str = args.date
        if not date_str:
            from datetime import date
            date_str = date.today().isoformat()
        post_carousel(date_str, args.caption or None, args.schedule or None)
    elif args.text:
        access_token, err = get_valid_token()
        if err:
            print(f"❌ {err}")
            sys.exit(1)
        person_urn, err = get_person_urn(access_token)
        if err:
            print(f"❌ {err}")
            sys.exit(1)
        post_urn, err = create_text_post(access_token, person_urn, args.text)
        if err:
            print(f"❌ {err}")
        else:
            print(f"✅ Text posted! URN: {post_urn}")
    else:
        parser.print_help()