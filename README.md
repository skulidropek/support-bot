# Telegram Support Bot

A Telegram support bot that automatically creates topics in a supergroup for each user and enables dialogue between users and the support team.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/skulidropek/support-bot
```

2. Create virtual environment
```bash
# Navigate to project directory
cd support-bot

# Create virtual environment
py -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `config.env` file with the following variables:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
SUPPORT_GROUP_ID=support_group_id
```

## Setup

1. Create a bot through [@BotFather](https://t.me/BotFather) and get the token
2. Create a Telegram supergroup and enable forum topics
3. Add the bot to the group and make it an administrator
4. Get the group ID (you can use the `/chatid` command in the group)
5. Add the token and group ID to the `config.env` file

## Running the Bot

```bash
py bot.py
```

## Usage

### For Users:
- Start a conversation with the bot using `/start`
- Send your question or support request

### For Support Team:
- All user messages appear in dedicated topics in the group
- Reply directly in the topic
- Responses are automatically forwarded to the user
- Each user has a single persistent topic for better organization

## Database Structure

### user_topics Table
- user_id: Telegram user ID
- topic_id: Group topic ID
- created_at: Creation timestamp

### messages Table
- id: Message ID
- user_id: Telegram user ID
- topic_id: Group topic ID
- message_text: Message content
- is_from_support: Support team message flag
- created_at: Message timestamp

## Technical Requirements
- python-telegram-bot==20.7
- python-dotenv==1.0.0
- aiosqlite==0.19.0

## Error Handling
- Automatic error logging
- User-friendly error messages
- Database connection error handling
- Message delivery confirmation

## Security

- Environment variables for sensitive data
- SQLite database for data persistence
- Input validation and sanitization
- Error message sanitization

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
