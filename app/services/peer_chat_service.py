import math
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

from app.models.peer_chat import (
    UserLocation, PeerChatRoom, PeerChatMember,
    PeerMessage, ChatRequest, UserStatus, RequestStatus,
)
from app.models.user import User
from app.database import SessionLocal
from app.logger import logger


SYNTHETIC_LOCATIONS = [
    (46.825039, 103.849974),
    (46.695232, 103.521231),
    (46.621589, 104.260902),
    (46.660773, 106.589494),
    (46.303936, 111.767188),
    (48.147065, 103.822578),
    (47.928782, 97.9874),
    (45.604004, 99.028418),
    (43.737186, 103.137698),
    (50.03787, 100.069435),
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


class PeerChatService:
    def update_user_location(self, user_id: int, latitude: float, longitude: float) -> UserLocation:
        db = SessionLocal()
        try:
            location = db.query(UserLocation).filter(UserLocation.user_id == user_id).first()
            if location:
                location.latitude = latitude
                location.longitude = longitude
                location.status = UserStatus.ONLINE.value
                location.last_active = datetime.utcnow()
                location.updated_at = datetime.utcnow()
            else:
                location = UserLocation(
                    user_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                    status=UserStatus.ONLINE.value,
                    last_active=datetime.utcnow(),
                )
                db.add(location)
            db.commit()
            db.refresh(location)
            return location
        finally:
            db.close()

    def set_user_status(self, user_id: int, status: str) -> None:
        db = SessionLocal()
        try:
            location = db.query(UserLocation).filter(UserLocation.user_id == user_id).first()
            if location:
                location.status = status
                location.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def search_peers(self, user_id: int, latitude: float, longitude: float, range_km: float) -> List[dict]:
        db = SessionLocal()
        try:
            all_locations = db.query(UserLocation).filter(
                UserLocation.user_id != user_id,
                UserLocation.status != UserStatus.OFFLINE.value,
            ).all()

            peers = []
            for loc in all_locations:
                distance = haversine(latitude, longitude, loc.latitude, loc.longitude)
                if distance <= range_km:
                    user = db.query(User).filter(User.user_id == loc.user_id).first()
                    if user:
                        peers.append({
                            "user_id": loc.user_id,
                            "username": user.username,
                            "name": user.name,
                            "profile_pic": user.profile_pic,
                            "distance_km": round(distance, 2),
                            "status": loc.status,
                            "latitude": loc.latitude,
                            "longitude": loc.longitude,
                        })

            return sorted(peers, key=lambda x: x["distance_km"])
        finally:
            db.close()

    def send_chat_request(self, from_user_id: int, to_user_id: int) -> ChatRequest:
        db = SessionLocal()
        try:
            existing = db.query(ChatRequest).filter(
                ChatRequest.from_user_id == from_user_id,
                ChatRequest.to_user_id == to_user_id,
                ChatRequest.status == RequestStatus.PENDING.value,
            ).first()
            if existing:
                return existing

            request = ChatRequest(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                status=RequestStatus.PENDING.value,
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            return request
        finally:
            db.close()

    def accept_chat_request(self, request_id: int, user_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            chat_request = db.query(ChatRequest).filter(
                ChatRequest.id == request_id,
                ChatRequest.to_user_id == user_id,
                ChatRequest.status == RequestStatus.PENDING.value,
            ).first()

            if not chat_request:
                return None

            room = db.query(PeerChatRoom).filter(PeerChatRoom.room_id == chat_request.room_id).first()
            if not room:
                room = PeerChatRoom(
                    name=f"Peer Chat Room",
                    created_by=chat_request.from_user_id,
                )
                db.add(room)
                db.commit()
                db.refresh(room)
                chat_request.room_id = room.room_id

            existing_member = db.query(PeerChatMember).filter(
                PeerChatMember.room_id == room.room_id,
                PeerChatMember.user_id == user_id,
            ).first()

            if not existing_member:
                member = PeerChatMember(
                    room_id=room.room_id,
                    user_id=user_id,
                    status="active",
                )
                db.add(member)

            from_member = db.query(PeerChatMember).filter(
                PeerChatMember.room_id == room.room_id,
                PeerChatMember.user_id == chat_request.from_user_id,
            ).first()

            if not from_member:
                from_member = PeerChatMember(
                    room_id=room.room_id,
                    user_id=chat_request.from_user_id,
                    status="active",
                )
                db.add(from_member)

            chat_request.status = RequestStatus.ACCEPTED.value
            chat_request.responded_at = datetime.utcnow()
            db.commit()

            return {
                "room_id": room.room_id,
                "name": room.name,
                "created_by": room.created_by,
            }
        finally:
            db.close()

    def reject_chat_request(self, request_id: int, user_id: int) -> bool:
        db = SessionLocal()
        try:
            chat_request = db.query(ChatRequest).filter(
                ChatRequest.id == request_id,
                ChatRequest.to_user_id == user_id,
                ChatRequest.status == RequestStatus.PENDING.value,
            ).first()

            if not chat_request:
                return False

            chat_request.status = RequestStatus.REJECTED.value
            chat_request.responded_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()

    def get_pending_requests(self, user_id: int) -> List[dict]:
        db = SessionLocal()
        try:
            requests = db.query(ChatRequest).filter(
                ChatRequest.to_user_id == user_id,
                ChatRequest.status == RequestStatus.PENDING.value,
            ).all()

            result = []
            for req in requests:
                from_user = db.query(User).filter(User.user_id == req.from_user_id).first()
                if from_user:
                    result.append({
                        "id": req.id,
                        "from_user_id": req.from_user_id,
                        "from_username": from_user.username,
                        "from_name": from_user.name,
                        "from_profile_pic": from_user.profile_pic,
                        "created_at": req.created_at.isoformat() if req.created_at else None,
                    })
            return result
        finally:
            db.close()

    def create_room(self, created_by: int) -> PeerChatRoom:
        db = SessionLocal()
        try:
            room = PeerChatRoom(created_by=created_by)
            db.add(room)
            db.commit()
            db.refresh(room)

            member = PeerChatMember(
                room_id=room.room_id,
                user_id=created_by,
                status="active",
            )
            db.add(member)
            db.commit()

            return room
        finally:
            db.close()

    def join_room(self, room_id: int, user_id: int) -> Optional[PeerChatMember]:
        db = SessionLocal()
        try:
            existing = db.query(PeerChatMember).filter(
                PeerChatMember.room_id == room_id,
                PeerChatMember.user_id == user_id,
            ).first()

            if existing:
                existing.status = "active"
                existing.left_at = None
                db.commit()
                db.refresh(existing)
                return existing

            member = PeerChatMember(
                room_id=room_id,
                user_id=user_id,
                status="active",
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            return member
        finally:
            db.close()

    def leave_room(self, room_id: int, user_id: int) -> bool:
        db = SessionLocal()
        try:
            member = db.query(PeerChatMember).filter(
                PeerChatMember.room_id == room_id,
                PeerChatMember.user_id == user_id,
            ).first()

            if not member:
                return False

            member.status = "left"
            member.left_at = datetime.utcnow()
            db.commit()

            active_members = db.query(PeerChatMember).filter(
                PeerChatMember.room_id == room_id,
                PeerChatMember.status == "active",
            ).count()

            if active_members == 0:
                room = db.query(PeerChatRoom).filter(PeerChatRoom.room_id == room_id).first()
                if room:
                    room.is_active = False
                    db.commit()

            return True
        finally:
            db.close()

    def send_message(self, room_id: int, sender_id: int, message: str) -> PeerMessage:
        db = SessionLocal()
        try:
            msg = PeerMessage(
                room_id=room_id,
                sender_id=sender_id,
                message=message,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            return msg
        finally:
            db.close()

    def get_room_messages(self, room_id: int, limit: int = 50) -> List[dict]:
        db = SessionLocal()
        try:
            messages = db.query(PeerMessage).filter(
                PeerMessage.room_id == room_id,
            ).order_by(PeerMessage.created_at.desc()).limit(limit).all()

            result = []
            for msg in messages:
                sender = db.query(User).filter(User.user_id == msg.sender_id).first()
                result.append({
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "sender_name": sender.name if sender else "Unknown",
                    "message": msg.message,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                })
            return list(reversed(result))
        finally:
            db.close()

    def get_user_rooms(self, user_id: int) -> List[dict]:
        db = SessionLocal()
        try:
            members = db.query(PeerChatMember).filter(
                PeerChatMember.user_id == user_id,
                PeerChatMember.status == "active",
            ).all()

            rooms = []
            for member in members:
                room = db.query(PeerChatRoom).filter(PeerChatRoom.room_id == member.room_id).first()
                if room and room.is_active:
                    other_members = db.query(PeerChatMember, User).join(
                        User, User.user_id == PeerChatMember.user_id
                    ).filter(
                        PeerChatMember.room_id == room.room_id,
                        PeerChatMember.user_id != user_id,
                        PeerChatMember.status == "active",
                    ).all()

                    other_users = []
                    for m, u in other_members:
                        other_users.append({
                            "user_id": u.user_id,
                            "username": u.username,
                            "name": u.name,
                            "profile_pic": u.profile_pic,
                        })

                    rooms.append({
                        "room_id": room.room_id,
                        "name": room.name,
                        "created_by": room.created_by,
                        "other_members": other_users,
                    })
            return rooms
        finally:
            db.close()

    def seed_synthetic_locations(self) -> None:
        db = SessionLocal()
        try:
            users = db.query(User).all()
            for i, user in enumerate(users):
                if i < len(SYNTHETIC_LOCATIONS):
                    lat, lon = SYNTHETIC_LOCATIONS[i]
                    location = db.query(UserLocation).filter(UserLocation.user_id == user.user_id).first()
                    if not location:
                        location = UserLocation(
                            user_id=user.user_id,
                            latitude=lat,
                            longitude=lon,
                            status=UserStatus.ONLINE.value,
                        )
                        db.add(location)
            db.commit()
            logger.info(f"Seeded {len(users)} synthetic user locations")
        finally:
            db.close()


peer_chat_service = PeerChatService()