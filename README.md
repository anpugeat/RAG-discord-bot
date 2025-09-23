# Intern Project: RAG-Based Discord Chatbot

Also as part of my work at Edue, I developed a Discord chatbot to interact with students and to moderate the Edue discord server, which I also devised to develop a community system. The server is intended as a space for students to congregate and discuss course material, including voice channels, homework/coursework discussion chats and group study rooms. This bot is designed to assist students by providing RAG-based answers to coursework questions, using textbooks as source material. For this Q&A, LlamaIndex is used for the RAG framework and document processing. Upon receiving a question, ChromaDB is used to perform a similarity search across the indexed documents, returning relevant chunks. This is fed into GPT-5 in addition to previous conversation context for a source-aware answer.  The bot also supports basic chat features using GPT-5 mini. This is on top of basic moderation features for the server, such as message rate limiting and profanity filters.

Future plans for the bot include implementing pomodoro timers, as well as auto-assigning roles to students based on their courses and interests.

---

## Project File Structure

```
edue-bot/
├── main.py                 # Bot entry point and initialization
├── requirements.txt        # Requirements
├── .env                    # Environment configuration (not in repo)
├── cogs/                   # Modular bot functionality
│   ├── chat.py             # Conversational AI with GPT-4o mini
│   ├── qa.py               # RAG-powered Q&A system
│   └── rate_limit.py       # Request rate limiting system
│
├── content/                # Educational documents for RAG - I have split them into
│   ├── assignments/        # into the following folder categories but divide this how 
│   ├── lecture_notes/      # wish, the bot will browse everything in the 'content' folder.
│   ├── research_papers/    
│   ├── textbooks/          
│   └── misc/               
│
├── data/                   # Runtime data storage
│   └── rate_limits.db      # SQLite database for rate limiting
│
└── chroma_db/              # ChromaDB vector storage
    └── [collection_data]   # Vector embeddings and metadata

```

## Config

You will need to create a .env file in the project root with the following variables:

```bash
# API Keys
DISCORD_BOT_TOKEN=bot_token_goes_here
OPENAI_API_KEY=openai_api_key_goes_here

# Prefix used for bot commands
BOT_PREFIX=!       

# Rate Limiting (requests per time period)
RATE_LIMIT_PER_MINUTE=5
RATE_LIMIT_PER_HOUR=30

# AI Model Configuration
CHAT_MODEL=gpt-5-mini-2025-08-07     # lighter, cheaper model for chat
QA_MODEL=gpt-5-2025-08-07            # model with stronger logic for Q&A

# Optional: File Processing Limits
MAX_FILE_SIZE=10485760
SUPPORTED_EXTENSIONS=.pdf,.docx,.txt,.md
```

## Installation

1. Clone the repository and navigate to the project directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env` file as described above
4. Add educational content such as textbooks to the `content/` directory for RAG content
5. Run the bot:
   ```bash
   python main.py
   ```
