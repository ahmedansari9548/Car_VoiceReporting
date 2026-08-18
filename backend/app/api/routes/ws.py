"""
WS /ws — WebSocket for continuous conversation.

Text:  {"text": "Corolla chahiye Lahore mein"}
Audio: raw binary bytes (webm/wav)

Server responds with full turn data including phase, cars, selected_car.
"""

import json
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.clients.groq import transcribe
from app.db.database import get_connection
from app.services.conversation import process_turn

router = APIRouter()

@router.websocket("/ws")
async def conversation_ws(websocket: WebSocket):
    await websocket.accept()
    conn = get_connection()
    session_id = None

    try:
        await websocket.send_json({"type": "connected", "message": "Ready"})

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # audio
            if "bytes" in message and message["bytes"]:
                try:
                    text = transcribe(message["bytes"])
                    if not text.strip():
                        await websocket.send_json({"type": "error", "message": "Could not understand audio"})
                        continue
                    await websocket.send_json({"type": "transcript", "text": text})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"STT failed: {e}"})
                    continue

            # text
            elif "text" in message and message["text"]:
                raw = message["text"]
                try:
                    text = json.loads(raw).get("text", "").strip()
                except json.JSONDecodeError:
                    text = raw.strip()
                if not text:
                    continue
            else:
                continue

            # process
            try:
                result = process_turn(conn, session_id, text)
                if session_id is None:
                    session_id = result.session_id

                await websocket.send_json({
                    "type": "turn",
                    "session_id": result.session_id,
                    "reply": result.reply,
                    "phase": result.phase,
                    "slots": {
                        k: {"value": v.value, "source": v.source.value, "confidence": v.confidence}
                        for k, v in result.slots.items()
                    },
                    "cars": result.cars,
                    "total_results": result.total_results,
                    "selected_car": result.selected_car,
                    "inspection": result.inspection,
                    "pakwheels_url": result.pakwheels_url,
                })
            except Exception as e:
                print(traceback.format_exc())
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
    finally:
        conn.close()