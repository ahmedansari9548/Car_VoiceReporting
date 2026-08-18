# PakWheels Voice Agent Backend

A FastAPI-based conversational backend for PakWheels that enables users to buy or sell cars using natural language or voice.

The system extracts structured information from conversations, validates vehicle details, maintains conversation state, and generates responses for both buyers and sellers.

---

## Features

- Voice-to-Text (Groq Whisper)
- Multi-turn conversation
- Buy flow
- Sell flow
- Slot filling
- Conversation memory
- Inventory search
- Automatic car specification lookup
- PakWheels search URL generation
- Listing description generation
- PostgreSQL persistence

---

## Tech Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Groq API
- Uvicorn

---

## Project Structure

```
backend/
│
├── app/
│   ├── api/
│   │   ├── turn.py
│   │   ├── transcribe.py
│   │   ├── listing.py
│   │   ├── websocket.py
│   │   └── search.py
│   │
│   ├── services/
│   │   ├── conversation.py
│   │   ├── groq.py
│   │   ├── catalog.py
│   │   ├── validation.py
│   │   ├── describe.py
│   │   └── search_url.py
│   │
│   ├── repositories/
│   │   ├── session_repo.py
│   │   ├── turn_repo.py
│   │   └── inventory_repo.py
│   │
│   ├── models/
│   ├── schemas/
│   └── config/
│
├── main.py
├── requirements.txt
├── README.md
└── .env
```

---

## Conversation Flow

```
User Voice
      │
      ▼
Speech-to-Text
      │
      ▼
POST /api/transcribe
      │
      ▼
Extracted Text
      │
      ▼
POST /api/turns
      │
      ▼
Conversation Engine
      │
      ▼
Intent Detection
      │
      ▼
Slot Extraction
      │
      ▼
Catalog Autofill
      │
      ▼
Validation
      │
      ▼
Session Update
      │
      ▼
Response
```

---

## API Endpoints

### Speech to Text

```
POST /api/transcribe
```

Converts recorded audio into text.

---

### Conversation

```
POST /api/turns
```

Processes the conversation and returns the assistant's next response.

---

### Listing Preview (Optional)

```
GET /api/listing/{session_id}
```

Returns the completed vehicle listing.

---

## Running Locally

### Clone

```bash
git clone <repository-url>
cd backend
```

### Create Virtual Environment

```bash
python -m venv venv
```

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

---

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Configure Environment

Create a `.env` file.

Example:

```env
GROQ_API_KEY=your_api_key

DATABASE_URL=postgresql://username:password@localhost:5432/pakwheels

MODEL_NAME=llama-3.3-70b-versatile
```

---

### Run

```bash
uvicorn main:app --reload
```

Backend:

```
http://localhost:8000
```

Swagger:

```
http://localhost:8000/docs
```

---

## Voice Development

Expose the backend publicly using ngrok.

```bash
ngrok http 8000
```

Example:

```
https://xxxx.ngrok-free.app
```

The frontend should use this URL during development.

---

## Buy Flow

1. User asks for a car.
2. Intent is detected.
3. Vehicle preferences are extracted.
4. Required fields are collected.
5. Inventory is searched.
6. Matching vehicles are returned.
7. If no results exist, a PakWheels search URL is generated.

---

## Sell Flow

1. User wants to sell a vehicle.
2. Vehicle information is collected.
3. Specifications are automatically completed.
4. Missing fields are requested.
5. Description is generated.
6. Listing is returned.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| GROQ_API_KEY | Groq API Key |
| DATABASE_URL | PostgreSQL connection string |
| MODEL_NAME | LLM used for extraction |

---

## Future Improvements

- Text-to-Speech (TTS)
- Streaming responses
- WebSocket support
- Authentication
- Docker deployment
- Redis caching
- Vehicle recommendation engine
- Analytics dashboard

---

## License

Internal project for PakWheels Voice Agent MVP.