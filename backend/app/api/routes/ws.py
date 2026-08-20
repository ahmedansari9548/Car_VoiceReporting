"""
app/api/routes/ws.py

WS /ws — WebSocket for continuous conversation.

Text:  {"text": "مجھے کرولا چاہیے لاہور میں"}
Audio: raw binary bytes (webm/wav/mp4)

Server responds with full turn data including phase, cars, selected_car.

FIXES vs the previous version
  1. get_connection() now runs INSIDE the try block. Previously a DB failure
     raised after accept(), so the socket died a millisecond after the
     handshake and the client sat in an endless reconnect loop that looked
     exactly like "the frontend can't connect".
  2. process_turn() is synchronous and takes seconds (LLM round trip). It now
     runs in a threadpool so it does not block the event loop — without this
     a second client cannot even complete a handshake while the first is
     mid-turn.
  3. Sends {"type": "ready"} only after the DB is actually usable, and a
     {"type": "pong"} so the client can measure latency.
"""

import json
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.clients.groq import transcribe
from app.db.database import get_connection
from app.services.conversation import process_turn

router = APIRouter()


@router.websocket("/ws")
async def conversation_ws(websocket: WebSocket):
    await websocket.accept()

    conn = None
    session_id = None

    try:
        # ── DB first, and inside the try: if this fails the client gets a
        #    real error message instead of a silent disconnect ──
        try:
            conn = get_connection()
        except Exception as e:
            print(f"[WS] database unavailable: {e}")
            await websocket.send_json({
                "type": "error",
                "fatal": True,
                "message": "Backend database is unavailable. Try again shortly.",
            })
            await websocket.close(code=1011)
            return

        await websocket.send_json({"type": "connected", "message": "Ready"})

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # ── audio ──
            if message.get("bytes"):
                try:
                    text = await run_in_threadpool(transcribe, message["bytes"])
                    if not text.strip():
                        await websocket.send_json({
                            "type": "error",
                            "message": "No speech detected. Hold the mic and speak clearly.",
                        })
                        continue
                    await websocket.send_json({"type": "transcript", "text": text})
                except Exception as e:
                    print(f"[WS] STT failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Could not transcribe that audio: {e}",
                    })
                    continue

            # ── text ──
            elif message.get("text"):
                raw = message["text"]
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {"text": raw}

                # Client heartbeat — lets the UI show a live latency figure
                # without touching the conversation pipeline.
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "t": payload.get("t")})
                    continue

                text = (payload.get("text") or "").strip()
                if not text:
                    continue
            else:
                continue

            # ── process ──
            try:
                result = await run_in_threadpool(process_turn, conn, session_id, text)
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
    except Exception:
        print(traceback.format_exc())
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
