# Peer Chat Feature Implementation Guide

## Training an Intern

This guide explains how to implement a peer discovery and real-time chat feature that allows users to find other learners nearby and chat with them.

---

## Feature Overview

Users can:
1. Set their location (latitude/longitude)
2. Search for peers within a specified radius (in km)
3. Send chat requests to nearby users
4. Accept/reject requests to form chat rooms
5. Send real-time messages via WebSocket
6. Leave rooms (room deletes when all users leave)

---

## Step 1: Database Models

### Why this step is necessary?

Before we can store any data, we need to define the structure of our data. Database models are the foundation of any application - they define how data is stored, how different pieces of data relate to each other, and ensure data integrity through constraints like foreign keys and indexes.

Without proper database design, we wouldn't be able to:
- Track where each user is located
- Create and manage chat rooms
- Store messages for history
- Handle the request/accept/reject flow

### What is the outcome?

We create 5 database tables that work together to support the entire feature. Each table has a specific purpose and they connect through foreign keys.

---

Create a new file `app/models/peer_chat.py`.

We need 5 tables to handle this feature:

### 1. UserLocation
Stores user location and online status.

This table is essential because:
- We need to know where each user is located to enable distance-based searching
- The status field (online/away/offline) helps users know when their peers are available
- We track last_active to know when a user was last seen

```python
class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, default="offline")  # online, away, offline
    last_active = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key decisions:**
- Indexed user_id for fast lookups
- Updated_at auto-updates when location changes
- Default status is "offline" until user explicitly updates

### 2. PeerChatRoom
Represents a chat room. Marked inactive when all users leave.

This table:
- Acts as the container for conversations
- Stores who created the room (useful for permissions)
- is_active flag lets us soft-delete rooms instead of hard delete

```python
class PeerChatRoom(Base):
    __tablename__ = "peer_chat_rooms"

    room_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

**Why soft delete?**
When all users leave a room, we mark it inactive rather than deleting. This preserves message history even if the room is no longer active.

### 3. PeerChatMember
Tracks which users are in which room.

This is a many-to-many relationship table between users and rooms:
- A user can be in multiple rooms
- A room can have multiple users

The status field tracks whether a user is currently active or has left (allows re-joining).

```python
class PeerChatMember(Base):
    __tablename__ = "peer_chat_members"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("peer_chat_rooms.room_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, left
```

**Why track left_at?**
This timestamp lets us know exactly when a user left, which can be useful for analytics or displaying "last seen" information.

### 4. PeerMessage
Stores messages in database for history.

Storing messages in the database rather than just in memory has several benefits:
- Users can view message history even after disconnecting
- Messages persist across app restarts
- Useful for debugging issues

```python
class PeerMessage(Base):
    __tablename__ = "peer_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("peer_chat_rooms.room_id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Why index room_id and sender_id?**
Both are frequently used in queries - room_id for fetching messages in a room, sender_id for finding messages by a specific user.

### 5. ChatRequest
Handles the request/accept/reject flow.

This table manages the lifecycle of a chat request:
- Pending: request sent, waiting for response
- Accepted: request accepted, room created
- Rejected: request declined

```python
class ChatRequest(Base):
    __tablename__ = "chat_requests"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("peer_chat_rooms.room_id"), nullable=True)
    status = Column(String, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
```

**Why separate request from room?**
This allows us to track the request lifecycle independently. The room_id is added only after the request is accepted.

### Import Models in main.py

The database tables won't be created automatically. We need to import these models in main.py so SQLAlchemy knows about them when creating tables.

Add to `app/main.py`:

```python
from app.models.peer_chat import (
    UserLocation, PeerChatRoom, PeerChatMember,
    PeerMessage, ChatRequest,
)
```

When FastAPI starts, it runs `Base.metadata.create_all(bind=engine)` which creates all tables for any imported models.

---

## Step 2: Service Layer

### Why this step is necessary?

The service layer acts as the bridge between the API endpoints (routers) and the database. It contains all the business logic - the actual operations that manipulate data. Keeping this separate from the router has several benefits:

1. **Separation of concerns**: Routers handle HTTP requests/responses, services handle data operations
2. **Reusability**: Service methods can be called from multiple places (WebSocket, REST, other services)
3. **Testability**: Services can be unit tested without requiring HTTP requests
4. **Cleaner code**: Router code stays focused on request handling

### What is the outcome?

A service file that handles all data operations - location updates, peer search, room management, messaging, etc.

---

Create `app/services/peer_chat_service.py`.

### Distance Calculation (Haversine Formula)

**Why do we need this?**

When a user searches for peers, we need to calculate the distance between their location and other users' locations. The Earth is a sphere, so we can't just use straight-line distance. The Haversine formula calculates the great-circle distance between two points on a sphere given their latitudes and longitudes.

This is essential for the "find peers within X km" feature.

```python
import math

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth's radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
```

**How it works:**
1. Convert latitudes/longitudes from degrees to radians
2. Calculate the difference in latitude and longitude
3. Apply the Haversine formula using trigonometry
4. Multiply by Earth's radius (6371 km) to get distance

### Key Service Methods

1. **update_user_location(user_id, latitude, longitude)** - Save/update user location
   - Creates new location record if doesn't exist, updates existing one
   - Sets status to "online" automatically

2. **set_user_status(user_id, status)** - Set online/away/offline
   - Used by WebSocket to mark user status based on connection state

3. **search_peers(user_id, latitude, longitude, range_km)** - Find peers within range
   - Queries all users except current user who aren't offline
   - Calculates distance using haversine for each
   - Filters by range_km and sorts by distance

4. **send_chat_request(from_user_id, to_user_id)** - Create a request
   - Checks for existing pending requests to prevent duplicates

5. **accept_chat_request(request_id, user_id)** - Accept and create room
   - Creates room if not exists, adds both users as members
   - Updates request status to "accepted"

6. **reject_chat_request(request_id, user_id)** - Reject request
   - Simple status update to "rejected"

7. **get_pending_requests(user_id)** - Get incoming requests
   - Returns all pending requests sent to the user

8. **join_room(room_id, user_id)** - Add user to room
   - Creates new member record or reactivates existing left member

9. **leave_room(room_id, user_id)** - Remove user, delete room if empty
   - Marks member as "left"
   - Checks if any active members remain
   - If none, marks room as inactive

10. **send_message(room_id, sender_id, message)** - Store message
    - Creates message record in database

11. **get_room_messages(room_id, limit)** - Get message history
    - Returns messages in chronological order with sender info

12. **get_user_rooms(user_id)** - Get all rooms for user
    - Returns active rooms with other member information

### Important Implementation Details

- Use **separate database sessions** for each operation (don't pass DB around)
  - Each service method creates its own SessionLocal()
  - This prevents session management issues and ensures clean transactions

- Return **dictionaries** from service methods, not ORM objects
  - Returning SQLAlchemy objects can cause "not bound to session" errors
  - Converting to dicts before returning makes the API more stable

- Delete room when all users leave
  - After marking a member as left, check active member count
  - If 0, set room.is_active = false

---

## Step 3: Router/API Endpoints

### Why this step is necessary?

Routers are the entry points for API requests. They handle:
- HTTP method routing (GET, POST, etc.)
- Request validation
- Authentication (JWT)
- Response formatting
- Calling service methods

Without routers, there would be no way for client applications to interact with our service.

### What is the outcome?

RESTful API endpoints plus a WebSocket endpoint for real-time communication.

---

Create `app/routers/peer_chat.py`.

### WebSocket Endpoint

**Why do we need WebSocket?**

HTTP is request-response based - the client makes a request, server responds, connection closes. For real-time chat where messages need to be sent instantly without the client polling, we need a persistent connection. WebSocket provides exactly that.

Once connected, the server can push messages to the client at any time.

```python
from fastapi import WebSocket, WebSocketDisconnect

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

            if message_data["type"] == "message":
                # Save to DB and broadcast to room
                pass
            elif message_data["type"] == "join_room":
                # Add to room_connections
                pass
            elif message_data["type"] == "leave_room":
                # Remove from room_connections
                pass
    except WebSocketDisconnect:
        peer_chat_service.set_user_status(user_id, "away")
        # Clean up connections
```

**How it works:**
1. `active_connections` maps user_id to their WebSocket - lets us send messages to specific users
2. `room_connections` maps room_id to set of user_ids - lets us broadcast to all in a room
3. When user disconnects, status changes to "away" but they remain in the room

### REST Endpoints

These endpoints allow clients to perform all operations via HTTP:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/peer/location?latitude=&longitude=` | Update user location |
| GET | `/peer/search?latitude=&longitude=&range_km=` | Search peers within range |
| POST | `/peer/request?to_user_id=` | Send chat request |
| GET | `/peer/requests` | Get pending requests |
| POST | `/peer/request/{id}/accept` | Accept request |
| POST | `/peer/request/{id}/reject` | Reject request |
| GET | `/peer/rooms` | Get user's rooms |
| GET | `/peer/rooms/{id}/messages` | Get message history |
| POST | `/peer/rooms/{id}/messages?message=` | Send message (HTTP) |
| POST | `/peer/rooms/{id}/join` | Join room |
| POST | `/peer/rooms/{id}/leave` | Leave room |

### Authentication

All endpoints use `Depends(get_current_user)` to protect routes with JWT.

**Why authenticate every request?**
- Ensures only logged-in users can access the feature
- Provides user_id for all operations (who is making the request)
- Prevents unauthorized access to private data

---

## Step 4: Register Router

### Why this step is necessary?

Even though we created the router file, it won't be active until we register it with FastAPI. This connects the router to the application and makes all endpoints available.

### What is the outcome?

All peer chat endpoints become accessible at `/api/v1/peer/*`

---

In `app/main.py`:

```python
from app.routers.peer_chat import router as peer_chat_router
app.include_router(peer_chat_router, prefix="/api/v1/peer", tags=["peer_chat"])
```

**Key points:**
- `prefix="/api/v1/peer"` adds /api/v1/peer to all routes in this router
- `tags=["peer_chat"]` groups these endpoints in API documentation

---

## Step 5: Push Notifications

### Why this step is necessary?

When user A sends a chat request to user B, user B needs to know about it. Without notifications, user B would have to manually check for pending requests. Push notifications provide instant awareness.

We already have a notification service in the codebase - we just need to use it.

### What is the outcome?

Users receive push notifications when:
- They receive a new chat request
- Their chat request is accepted

---

Reuse existing notification service. When a request is sent or accepted:

```python
from app.services.notification_service import notification_service

to_user = db.query(User).filter(User.user_id == to_user_id).first()
if to_user and to_user.fcm_token:
    notification_service.send_push_notification(
        fcm_token=to_user.fcm_token,
        title="New Chat Request",
        message=f"{user.name} wants to practice English with you!",
        data={"type": "chat_request", "request_id": request_id},
    )
```

**How it works:**
- Checks if user has an FCM token (device push token)
- Sends push notification with title, message, and data payload
- The data payload lets the app handle navigation when user taps the notification
- In development mode without Firebase, it logs to console

---

## Step 6: Fix JWT Sub Claim

### Why this step is necessary?

When we changed user_id from a string to an auto-incrementing integer, we broke the JWT token generation. The JWT specification (RFC 7519) requires the "sub" (subject) claim to be a string.

This is a common issue when migrating from string to integer IDs.

### What is the outcome?

JWT tokens work correctly with integer user IDs.

---

Since user_id is now an integer, the JWT `sub` claim must be a string:

In `app/routers/auth.py`, change all token creation:

```python
access_token = create_access_token(
    data={"sub": str(user.user_id)},  # Convert to string
    expires_delta=access_token_expires,
)
```

In `app/auth.py`, when decoding:

```python
user_id = int(payload.get("sub"))  # Convert back to int
```

**Why both directions?**
- Creating: Must be string (JWT spec requirement)
- Reading: Convert back to int (our database uses integer)

---

## Testing the Feature

### Manual Testing Order

1. **Register/Login** two users (Alice & Bob)
2. **Update locations** for both
3. **Search peers** - Alice searches, sees Bob if within range
4. **Send request** - Alice sends to Bob
5. **Check requests** - Bob sees pending request
6. **Accept request** - Bob accepts, room created
7. **Check rooms** - Both see the room
8. **Send messages** - Test HTTP endpoint
9. **Get messages** - Verify stored in DB
10. **Leave room** - Both leave, room marked inactive

### cURL Examples

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "pass123"}'

# Update location
curl -X POST "http://localhost:8000/api/v1/peer/location?latitude=46.825039&longitude=103.849974" \
  -H "Authorization: Bearer TOKEN"

# Search peers
curl -s "http://localhost:8000/api/v1/peer/search?latitude=46.825039&longitude=103.849974&range_km=50" \
  -H "Authorization: Bearer TOKEN"

# Send request
curl -X POST "http://localhost:8000/api/v1/peer/request?to_user_id=2" \
  -H "Authorization: Bearer TOKEN"

# Accept request
curl -X POST "http://localhost:8000/api/v1/peer/request/1/accept" \
  -H "Authorization: Bearer TOKEN"

# Send message
curl -X POST "http://localhost:8000/api/v1/peer/rooms/1/messages?message=Hello" \
  -H "Authorization: Bearer TOKEN"
```

---

## Key Design Decisions

1. **Store messages in DB** - Allows users to see chat history
2. **Delete room when all leave** - Saves storage, simpler logic
3. **Use WebSocket for real-time** - FastAPI has built-in support
4. **Separate service from router** - Clean separation of concerns
5. **Return dicts from service** - Avoids SQLAlchemy session issues

---

## Synthetic Seed Data

### Why this is necessary?

During development and testing, we don't have real users with real GPS locations. To test the peer discovery feature, we need users with locations spread out at different distances. Instead of manually adding location data for each test user or building a complex location input UI, we use synthetic (fake) data.

### What is the outcome?

We have 10 predefined latitude/longitude coordinates representing different cities in Mongolia. When the application starts, these coordinates are automatically assigned to the first 10 users in the database. This allows testers to verify the distance-based search works correctly by placing users at known distances from each other.

### Implementation

In the peer_chat_service.py, we define a list of coordinate tuples:

```python
SYNTHETIC_LOCATIONS = [
    (46.825039, 103.849974),  # Ulaanbaatar area
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
```

The `seed_synthetic_locations()` method runs at startup, iterating through existing users and assigning each a location from this list. In production, this would be replaced or supplemented by real GPS data from mobile devices. The coordinates are intentionally placed at varying distances from each other so we can verify that the distance calculation correctly identifies which users are within a given range and which are not.

---

## WebSocket Message Broadcasting Flow

### Why this step is necessary?

Understanding how messages flow through the system is crucial for debugging and scaling. The broadcasting mechanism is what makes real-time chat possible - without it, users would have to constantly poll the server to check for new messages.

### What is the outcome?

When a user sends a message, it instantly appears on all other users' screens who are in the same room.

### How it works

The broadcasting flow works in several steps. First, the sender's client sends a JSON message through their WebSocket connection containing the message type, room ID, and message content. The WebSocket endpoint receives this message and parses the JSON. Then, for "message" type events, the endpoint calls the peer_chat_service.send_message() method which saves the message to the database. The service returns a complete message object including the sender's name and timestamp. Finally, the endpoint iterates through all user IDs in room_connections[room_id] and sends the message through each user's WebSocket connection stored in active_connections.

```python
# Simplified broadcasting logic
for uid, conn in active_connections.items():
    if uid in room_connections.get(room_id, set()):
        await conn.send_json({
            "type": "message",
            "room_id": room_id,
            "sender_id": user_id,
            "sender_name": sender.name,
            "message": content,
            "timestamp": saved_msg.created_at.isoformat(),
        })
```

This is a simple broadcast-to-all approach. In production, you might want to add: message deduplication to prevent double delivery, delivery receipts to confirm messages were received, offline message queuing for users who are temporarily disconnected, and message typing indicators to show when someone is composing a reply.

---

## FCM Tokens and Push Notifications

### Why this step is necessary?

Push notifications are essential for a chat application because users can't be expected to constantly check the app for new messages or requests. When someone sends a chat request or messages you, you should be notified immediately even if the app is closed.

### What is the outcome?

Users receive push notifications on their devices when they receive a new chat request or when their request is accepted.

### How FCM tokens work

Firebase Cloud Messaging (FCM) provides a way to send push notifications to mobile devices. Each device that installs the app gets a unique FCM token (also called a device token). This token is stored in the user's record in the database under the fcm_token field. When we need to send a notification, we use this token to tell Firebase exactly which device to deliver the message to.

```python
# In the user model
fcm_token = Column(String, nullable=True)  # Stored when user logs in from mobile
```

When sending a notification:

```python
to_user = db.query(User).filter(User.user_id == to_user_id).first()
if to_user and to_user.fcm_token:
    notification_service.send_push_notification(
        fcm_token=to_user.fcm_token,
        title="New Chat Request",
        message=f"{user.name} wants to practice English with you!",
        data={"type": "chat_request", "request_id": request_id},
    )
```

The notification payload contains a title, message body, and a data dictionary. This data dictionary is important because when the user taps the notification, the app knows exactly what action to take (in this case, opening the chat request screen). In development mode without Firebase configured, the notification service simply logs the notification to the console instead of actually sending it.

---

## Error Handling

### Why this step is necessary?

API endpoints must handle various error scenarios gracefully. Users will encounter situations like invalid tokens, non-existent resources, or missing required data. How we handle these errors determines whether the application feels robust and user-friendly or broken and confusing.

### What is the outcome?

Users receive meaningful error messages and appropriate HTTP status codes for different failure scenarios.

### Common Error Cases

When a JWT token is invalid or expired, FastAPI's dependency injection automatically returns a 401 Unauthorized response with "Could not validate credentials" message. This happens because the get_current_user function raises an HTTPException when the token cannot be decoded or the user doesn't exist in the database.

When a user is not found, we manually check and return a 404 Not Found with an appropriate message like "User not found" or "Room not found". This is done in each service method before proceeding with the operation.

When a room doesn't exist, attempting to join a non-existent room returns an error message "Room not found". Similarly, if a user tries to leave a room they're not a member of, they get "Not a member of this room" error.

For database errors like connection failures or constraint violations, we have a global exception handler in main.py that catches SQLAlchemyError and returns a generic 500 Internal Server Error with "Database error occurred" message - we don't expose internal database details to users for security reasons.

Request validation errors like missing parameters or invalid data types are handled by FastAPI's built-in RequestValidationError handler which returns a 422 Unprocessable Entity with details about what was wrong with the request.

Each error response follows the consistent format: {"status": "0", "data": null, "message": "Error description"}.

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| JWT error "Subject must be a string" | Convert user_id to string when creating token |
| "Instance not bound to session" | Return dicts from service, not ORM objects |
| Room not showing for requester | Add both users as members when accepting |
| Room not deleting | Check `active_members` count after each leave |

---

# Interview Q&A Practice

---

## Q1: How do you calculate distance between two coordinates?

**Answer:**
We use the Haversine formula, which calculates the great-circle distance between two points on a sphere given their latitudes and longitudes. The Earth is not flat, so regular Euclidean distance doesn't work for geographic coordinates. The formula accounts for the Earth's curvature by treating it as a sphere with a radius of 6371 kilometers. We convert the latitude and longitude values from degrees to radians, apply trigonometric formulas to calculate the central angle between the two points, and multiply by Earth's radius to get the distance in kilometers. This is essential for the "find peers within X kilometers" feature, where we need to filter users based on their proximity to the requesting user.

```python
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c
```

This returns distance in kilometers.

---

## Q2: How does the WebSocket handle real-time messaging?

**Answer:**
FastAPI provides built-in WebSocket support that allows for persistent, bidirectional communication between the server and clients. Unlike HTTP where the client always initiates requests, WebSocket allows the server to push messages to clients at any time. In our implementation, we maintain two dictionaries: one maps user IDs to their active WebSocket connections (active_connections), and another maps room IDs to sets of user IDs who are currently in that room (room_connections). When a user sends a message, we look up all users in that room from room_connections and send the message through their individual WebSocket connections stored in active_connections. We also handle WebSocketDisconnect exceptions to clean up when users go offline, removing them from active_connections and updating their status to "away" in the database.

```python
@router.websocket("/ws/peer-chat")
async def websocket_endpoint(websocket: WebSocket, token: str, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            # Process and broadcast
    except WebSocketDisconnect:
        # Clean up
```

---

## Q3: How do you handle the chat request flow?

**Answer:**
The chat request flow implements a request-accept-reject pattern that controls how users start conversations. First, when a user searches and finds another user they'd like to chat with, they send a chat request which creates a ChatRequest record in the database with status "pending". This record stores who sent the request, who it's for, and the current status. The recipient receives a push notification alerting them of the incoming request. If they choose to accept, we create a new PeerChatRoom and add both users as PeerChatMember records with "active" status. The request status is updated to "accepted" and the room_id is stored in the request record. If rejected, the status simply becomes "rejected". This design ensures that both users must consent to chat, preventing unwanted conversations and providing a better user experience.

---

## Q4: When is a chat room deleted?

**Answer:**
A room is deleted (technically marked inactive) when all users leave. In the `leave_room` service method, when a user leaves, we first mark their member record as "left" with a timestamp. Then we query the database to count how many active members remain in that specific room. If the count equals zero, meaning no users are currently active in the room, we set the room's is_active flag to false. This approach of soft-deleting (marking as inactive rather than hard-deleting) preserves the message history even after the room is no longer active. Users who previously left can see the conversation history but cannot rejoin since they're marked as "left" rather than "active".

---

## Q5: Why do you store messages in the database instead of just real-time?

**Answer:**
There are several important reasons for persisting messages in the database. First, message history allows users to review previous conversations even after disconnecting or closing the app - this is especially valuable in a language learning application where users might want to revisit corrections or vocabulary from past chats. Second, storing messages enables offline access - when users come back online after being offline, they can catch up on conversations they missed. Third, from a debugging perspective, having message records makes it much easier to investigate issues, track user behavior, or audit conversations. Finally, stored messages open up possibilities for future features like search functionality within chats, message analytics, or even training AI models on conversation data. The only downside is slightly more database storage, but the benefits far outweigh this minimal cost.

---

## Q6: How do you secure the WebSocket connection?

**Answer:**
WebSocket security is implemented by passing the JWT token and user_id as query parameters when establishing the connection (ws://localhost:8000/ws/peer-chat?token=...&user_id=...). Before accepting the WebSocket connection, the endpoint validates the JWT token to ensure the user is authenticated. The user_id is extracted and stored to identify which user owns this connection. In production environments, additional security measures would be recommended: using WSS (WebSocket Secure) for encrypted connections instead of unencrypted WS, implementing a heartbeat/ping-pong mechanism to detect broken connections quickly, adding rate limiting to prevent message flooding attacks, and implementing input validation and sanitization to prevent injection attacks.

---

## Q7: What happens if a user goes offline unexpectedly?

**Answer:**
When a WebSocket connection drops unexpectedly (such as losing internet connection, closing the app without disconnecting properly, or a network timeout), the WebSocketDisconnect exception is automatically raised by FastAPI. Our code catches this exception and performs several cleanup operations: it sets the user's status to "away" in the database, removes the user's WebSocket from active_connections dictionary, and removes the user from all room_connections sets. Importantly, the user is NOT removed from their chat rooms - they're simply marked as away. This means if they come back online within a reasonable time and the room is still active, they can reconnect and continue the conversation. The away status lets other users see that the person is currently offline but might return.

---

## Q8: How would you handle a group chat with more than 2 users?

**Answer:**
The current implementation already supports group chats without any modifications! The design is inherently many-to-many. When User A sends a request to User B and User B accepts, both are added as members to the same room. Later, User C can also send a request to either User A or User B, and when accepted, User C is also added to that same room. The room can continue accepting more users indefinitely. When any member sends a message, the broadcast logic sends it to all users in room_connections for that room, regardless of how many people are in it. The only change we'd need for better group experience would be to let users name the room (like "English Practice Group") instead of using the default "Peer Chat Room" name.

---

## Q9: What are the limitations of this implementation?

**Answer:**
This implementation has several limitations that would need to be addressed for production use. First, the in-memory connection storage (active_connections and room_connections dictionaries) won't work when scaling to multiple server instances because each server would have its own memory - you'd need Redis or another distributed state management system. Second, there's no pagination on message history, so as conversations grow, fetching all messages could become slow - you'd want to implement cursor-based pagination. Third, the distance search fetches all users from the database and then filters in Python, which doesn't scale - for production, you'd use PostGIS with spatial indexing for efficient radius queries. Fourth, the WebSocket uses unencrypted ws:// instead of secure wss:// protocol. Finally, there's no message read receipts or typing indicators beyond the basic "typing" event we implemented.

---

## Q10: Why did you convert user_id to string for JWT but store as integer in DB?

**Answer:**
This is necessary because of a conflict between two requirements. The JWT specification (RFC 7519) explicitly states that the "sub" (subject) claim must be a string value - this is a standard that all JWT libraries enforce. However, our database uses an auto-incrementing integer for user_id because integers are more efficient for primary keys, use less storage, and work naturally with auto-increment behavior. The solution is to convert the integer to string when creating the JWT token (str(user.user_id)), and convert it back to integer when decoding the token (int(payload.get("sub"))). This transformation happens at the boundaries of our system - the database and JWT handling - while internally everything works with integers. This is a common pattern when migrating from string-based IDs to integer-based IDs in systems that use JWT authentication.

---

# Summary

In this feature, you learned to:
- Design a relational database schema with multiple tables
- Implement distance calculation using Haversine formula
- Use FastAPI WebSocket for real-time communication
- Build a request/accept/reject flow
- Handle room lifecycle (create, join, leave, delete)
- Integrate push notifications
- Fix JWT token handling for integer user IDs

This pattern can be applied to many real-time features like notifications, live updates, and collaborative tools.