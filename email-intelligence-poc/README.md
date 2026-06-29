# Email Intelligence POC

A Python proof of concept that connects to an email mailbox, extracts messages, analyzes them with LangChain + Groq, and generates summary artifacts plus charts.

## Features

- IMAP mailbox integration for Gmail, Outlook, Yahoo, and other IMAP providers.
- Mock mailbox mode with varied fake messages for local development.
- LangChain analysis using `langchain-groq` and `ChatGroq`.
- Graceful no-key fallback that skips LLM summarization and uses local heuristic analysis for charts.
- PNG visualizations generated with pandas and matplotlib:
  - Sentiment distribution pie chart
  - Priority breakdown bar chart
  - Email volume over time line chart
  - Top senders bar chart

## Project structure

```text
email-intelligence-poc/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── email_client/
│   ├── __init__.py
│   ├── base.py
│   ├── imap_client.py
│   └── mock_client.py
├── chains/
│   ├── __init__.py
│   ├── summarizer.py
│   └── analyzer.py
├── visualization/
│   ├── __init__.py
│   └── charts.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

## Setup with uv

```bash
# install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# run with mock data (no credentials needed)
python main.py --mock

# run with live mailbox
python main.py
```

## Environment configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

`.env` is gitignored and must never be committed. It may contain mailbox credentials and API keys.

Supported variables:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
EMAIL_PROVIDER=imap
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_USE_SSL=true
```

### Groq API key

You can get a free Groq API key at [console.groq.com](https://console.groq.com/). It typically takes about 2 minutes and does not require a credit card.

If `GROQ_API_KEY` is not set, the app still fetches emails, prints raw email details, saves JSON outputs, and creates charts. LLM summarization is skipped in that mode.

## Run with mock data

Mock mode needs no credentials and is the fastest way to validate the POC:

```bash
python main.py --mock
```

You can limit the number of messages:

```bash
python main.py --mock --limit 10
```

## Run with a live mailbox

Configure `.env` with your IMAP settings, then run:

```bash
python main.py
```

Optional arguments:

```bash
python main.py --limit 50 --folder INBOX
```

## Gmail IMAP setup

1. In Gmail, open Settings > See all settings > Forwarding and POP/IMAP.
2. Enable IMAP and save changes.
3. Use a Google App Password for `EMAIL_PASSWORD`.
4. Do not use your real Google account password.
5. Set:

```dotenv
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USE_SSL=true
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

## Outputs

The app writes generated files to `output/`:

```text
output/
├── raw_emails.json
├── analyzed_emails.json
├── summary.json
└── charts/
    ├── sentiment_distribution.png
    ├── priority_breakdown.png
    ├── email_volume_over_time.png
    └── top_senders.png
```

## Example output

Placeholder for screenshots:

- Sentiment distribution chart
- Priority breakdown chart
- Email volume over time chart
- Top senders chart

The terminal also prints a concise report with fetched emails, summary source, priority, sentiment, topics, and saved output paths.
