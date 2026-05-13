import json
from typing import Dict, Set
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.peer_chat import UserLocation, PeerChatMember, PeerMessage
from app.services.peer_chat_service import peer_chat_service
from app.services.notification_service import notification_service
from app.utils.response import success, error
from app.logger import logger

router = APIRouter(tags=["peer_chat"])


active_connections: Dict[int, WebSocket] = {}
room_connections: Dict[int, Set[int]] = {}


@router.websocket("/ws/peer-chat")
async def websocket_endpoint(websocket: WebSocket, token: str, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket

    peer_chat_service.set_user_status(user_id, "online")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            msg_type = message_data.get("type")

            if msg_type == "message":
                room_id = message_data.get("room_id")
                content = message_data.get("message")

                saved_msg = peer_chat_service.send_message(room_id, user_id, content)

                sender = None
                db = next(get_db())
                try:
                    sender = db.query(User).filter(User.user_id == user_id).first()
                finally:
                    db.close()

                for uid, conn in active_connections.items():
                    if uid in room_connections.get(room_id, set()):
                        await conn.send_json({
                            "type": "message",
                            "room_id": room_id,
                            "sender_id": user_id,
                            "sender_name": sender.name if sender else "Unknown",
                            "message": content,
                            "timestamp": saved_msg.created_at.isoformat(),
                        })

            elif msg_type == "typing":
                room_id = message_data.get("room_id")
                for uid, conn in active_connections.items():
                    if uid != user_id and uid in room_connections.get(room_id, set()):
                        await conn.send_json({
                            "type": "typing",
                            "room_id": room_id,
                            "user_id": user_id,
                        })

            elif msg_type == "join_room":
                room_id = message_data.get("room_id")
                peer_chat_service.join_room(room_id, user_id)

                if room_id not in room_connections:
                    room_connections[room_id] = set()
                room_connections[room_id].add(user_id)

                await websocket.send_json({
                    "type": "joined",
                    "room_id": room_id,
                })

            elif msg_type == "leave_room":
                room_id = message_data.get("room_id")
                peer_chat_service.leave_room(room_id, user_id)

                if room_id in room_connections:
                    room_connections[room_id].discard(user_id)

                await websocket.send_json({
                    "type": "left",
                    "room_id": room_id,
                })

    except WebSocketDisconnect:
        peer_chat_service.set_user_status(user_id, "away")
        if user_id in active_connections:
            del active_connections[user_id]

        for room_id, members in list(room_connections.items()):
            if user_id in members:
                members.discard(user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        peer_chat_service.set_user_status(user_id, "away")
        if user_id in active_connections:
            del active_connections[user_id]


@router.post("/location")
def update_location(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    location = peer_chat_service.update_user_location(
        current_user.user_id, latitude, longitude
    )
    return success(data={
        "user_id": location.user_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "status": location.status,
    })


@router.get("/search")
def search_peers(
    latitude: float = Query(...),
    longitude: float = Query(...),
    range_km: float = Query(..., ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    peers = peer_chat_service.search_peers(
        current_user.user_id, latitude, longitude, range_km
    )
    return success(data={"peers": peers})


@router.post("/request")
def send_chat_request(
    to_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat_request = peer_chat_service.send_chat_request(
        current_user.user_id, to_user_id
    )

    to_user = db.query(User).filter(User.user_id == to_user_id).first()
    if to_user and to_user.fcm_token:
        notification_service.send_push_notification(
            fcm_token=to_user.fcm_token,
            title="New Chat Request",
            message=f"{current_user.name or current_user.username} wants to practice English with you!",
            data={"type": "chat_request", "request_id": chat_request.id},
        )

    return success(data={"request_id": chat_request.id})


@router.get("/requests")
def get_pending_requests(
    current_user: User = Depends(get_current_user),
):
    requests = peer_chat_service.get_pending_requests(current_user.user_id)
    return success(data={"requests": requests})


@router.post("/request/{request_id}/accept")
def accept_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = peer_chat_service.accept_chat_request(request_id, current_user.user_id)
    if not room:
        return error(message="Invalid request or already handled")

    from_user = db.query(User).filter(User.user_id == room["created_by"]).first()
    if from_user and from_user.fcm_token:
        notification_service.send_push_notification(
            fcm_token=from_user.fcm_token,
            title="Request Accepted!",
            message=f"{current_user.name or current_user.username} accepted your chat request!",
            data={"type": "request_accepted", "room_id": room["room_id"]},
        )

    peer_chat_service.join_room(room["room_id"], current_user.user_id)

    if room["room_id"] not in room_connections:
        room_connections[room["room_id"]] = set()

    return success(data={
        "room_id": room["room_id"],
        "created_by": room["created_by"],
    })


@router.post("/request/{request_id}/reject")
def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = peer_chat_service.reject_chat_request(request_id, current_user.user_id)
    if not result:
        return error(message="Invalid request or already handled")

    return success(message="Request rejected")


@router.get("/rooms")
def get_user_rooms(
    current_user: User = Depends(get_current_user),
):
    rooms = peer_chat_service.get_user_rooms(current_user.user_id)
    return success(data={"rooms": rooms})


@router.get("/rooms/{room_id}/messages")
def get_room_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    messages = peer_chat_service.get_room_messages(room_id, limit)
    return success(data={"messages": messages})


@router.post("/rooms/{room_id}/join")
def join_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
):
    member = peer_chat_service.join_room(room_id, current_user.user_id)
    if not member:
        return error(message="Room not found")
    return success(data={"room_id": room_id})


@router.post("/rooms/{room_id}/leave")
def leave_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
):
    result = peer_chat_service.leave_room(room_id, current_user.user_id)
    if not result:
        return error(message="Not a member of this room")

    if room_id in room_connections:
        room_connections[room_id].discard(current_user.user_id)

    return success(message="Left room successfully")


@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: int,
    message: str,
    current_user: User = Depends(get_current_user),
):
    msg = peer_chat_service.send_message(room_id, current_user.user_id, message)
    sender = None
    db = next(get_db())
    try:
        sender = db.query(User).filter(User.user_id == current_user.user_id).first()
    finally:
        db.close()

    return success(data={
        "id": msg.id,
        "sender_id": msg.sender_id,
        "sender_name": sender.name if sender else "Unknown",
        "message": msg.message,
        "created_at": msg.created_at.isoformat(),
    })