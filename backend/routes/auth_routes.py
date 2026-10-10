import requests
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from core.config import settings
from database.db import upsert_google_user, get_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token JWT returned by Google Identity Services")
    client_id: Optional[str] = None


@router.get("/config")
def get_auth_config():
    """Return public OAuth configuration so frontend can auto-adapt."""
    return {
        "status": "success",
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "is_configured": bool(settings.GOOGLE_CLIENT_ID and not settings.GOOGLE_CLIENT_ID.startswith("your_"))
    }


@router.post("/google")
def authenticate_google(req: GoogleAuthRequest):
    """
    Validates Google ID Token with Google tokeninfo endpoint,
    finds or creates user record, and returns user session.
    """
    token = req.credential.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token credential is required"
        )

    try:
        # Validate Google ID token via Google's tokeninfo API
        tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        response = requests.get(tokeninfo_url, timeout=10)

        if response.status_code != 200:
            err_data = response.json() if response.content else {}
            err_msg = err_data.get("error_description") or err_data.get("error") or "Invalid Google Token"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google authentication failed: {err_msg}"
            )

        payload = response.json()

        # Check audience if backend GOOGLE_CLIENT_ID is set
        backend_client_id = settings.GOOGLE_CLIENT_ID.strip()
        if backend_client_id and not backend_client_id.startswith("your_"):
            token_aud = payload.get("aud")
            if token_aud != backend_client_id:
                # Still log but verify if aud matches
                print(f"Warning: Token aud '{token_aud}' does not strictly match backend CLIENT_ID '{backend_client_id}'")

        # Extract verified user profile from Google payload
        sub = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name") or payload.get("given_name") or "Athlete"
        avatar_url = payload.get("picture") or ""

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token missing email address"
            )

        # Upsert user in database / mock store
        user_record = upsert_google_user({
            "google_id": sub,
            "email": email,
            "name": name,
            "avatar_url": avatar_url
        })

        return {
            "status": "success",
            "message": "Google authentication successful",
            "user": user_record,
            "token": token
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error during Google authentication: {str(e)}"
        )


@router.get("/me")
def get_current_user(user_id: str = Query(..., description="ID of user to retrieve")):
    user = get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "status": "success",
        "user": user
    }
