#!/usr/bin/env python3
"""
Slack Notifier for Fantasy Football Recaps
Sends weekly recaps to a Slack channel using Slack Webhook or Bot Token
"""

import os
import requests
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SlackNotifier:
    """Handles sending messages and recaps to Slack"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        channel: Optional[str] = None,
    ):
        """
        Initialize Slack notifier with either webhook URL or bot token

        Args:
            webhook_url: Slack Incoming Webhook URL (easier setup)
            bot_token: Slack Bot Token (more features, requires app installation)
            channel: Channel ID or name (required if using bot_token)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL")

        if not self.webhook_url and not self.bot_token:
            raise ValueError(
                "Either SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN must be provided. "
                "Set one in your .env file or pass as parameter."
            )

        if self.bot_token and not self.channel:
            raise ValueError(
                "SLACK_CHANNEL must be provided when using SLACK_BOT_TOKEN. "
                "Set it in your .env file or pass as parameter."
            )

    def send_message(self, text: str, blocks: Optional[list] = None) -> bool:
        """
        Send a simple text message to Slack

        Args:
            text: Plain text message (fallback text if blocks are used)
            blocks: Optional Slack Block Kit blocks for rich formatting

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            if self.webhook_url:
                return self._send_via_webhook(text, blocks)
            else:
                return self._send_via_bot_token(text, blocks)
        except Exception as e:
            print(f"❌ Error sending Slack message: {e}")
            return False

    def send_recap(self, week: int, recap_content: str) -> bool:
        """
        Send a weekly recap to Slack with nice formatting

        Args:
            week: Week number
            recap_content: The full recap markdown content

        Returns:
            bool: True if sent successfully, False otherwise
        """
        print(f"📤 Sending Week {week} recap to Slack...")

        # Extract headline from recap (first line)
        lines = recap_content.strip().split("\n")
        headline = lines[0].replace("#", "").strip() if lines else f"Week {week} Recap"

        # Format message for Slack
        # Slack uses a different markdown format, so we need to convert
        slack_content = self._convert_markdown_to_slack(recap_content)

        # Split into chunks if too long (Slack has 3000 char limit per message)
        chunks = self._split_content(slack_content, max_length=2900)

        # Send header block
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🏈 {headline}", "emoji": True},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Week {week} • Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                    }
                ],
            },
            {"type": "divider"},
        ]

        # Send first chunk with header
        success = self.send_message(
            text=f"Week {week} Fantasy Football Recap",
            blocks=blocks
            + [{"type": "section", "text": {"type": "mrkdwn", "text": chunks[0]}}],
        )

        if not success:
            return False

        # Send remaining chunks as follow-up messages
        for i, chunk in enumerate(chunks[1:], start=2):
            success = self.send_message(
                text=f"Week {week} Recap (continued {i}/{len(chunks)})",
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": chunk}}],
            )
            if not success:
                return False

        print(f"✅ Week {week} recap sent successfully to Slack!")
        return True

    def _send_via_webhook(self, text: str, blocks: Optional[list] = None) -> bool:
        """Send message using Incoming Webhook"""
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        response = requests.post(
            self.webhook_url, json=payload, headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            print(f"❌ Slack webhook error: {response.status_code} - {response.text}")
            return False

        return True

    def _send_via_bot_token(self, text: str, blocks: Optional[list] = None) -> bool:
        """Send message using Bot Token and chat.postMessage API"""
        payload = {"channel": self.channel, "text": text}
        if blocks:
            payload["blocks"] = blocks

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bot_token}",
            },
        )

        result = response.json()
        if not result.get("ok"):
            print(f"❌ Slack API error: {result.get('error', 'Unknown error')}")
            return False

        return True

    def _convert_markdown_to_slack(self, markdown: str) -> str:
        """
        Convert standard markdown to Slack's markdown format
        Slack uses slightly different syntax
        """
        # Slack uses *bold* and _italic_ (same as standard)
        # But headings need to be converted to bold text
        lines = []
        for line in markdown.split("\n"):
            # Convert headings to bold
            if line.startswith("###"):
                line = f"*{line.replace('###', '').strip()}*"
            elif line.startswith("##"):
                line = f"*{line.replace('##', '').strip()}*"
            elif line.startswith("#"):
                line = f"*{line.replace('#', '').strip()}*"

            lines.append(line)

        return "\n".join(lines)

    def _split_content(self, content: str, max_length: int = 2900) -> list:
        """
        Split content into chunks that fit Slack's message length limit
        Tries to split at paragraph boundaries when possible
        """
        if len(content) <= max_length:
            return [content]

        chunks = []
        current_chunk = ""
        paragraphs = content.split("\n\n")

        for para in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_chunk) + len(para) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    # Single paragraph is too long, split by sentences
                    sentences = para.split(". ")
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 > max_length:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += sentence + ". "
            else:
                current_chunk += para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def test_connection(self) -> bool:
        """Test the Slack connection by sending a test message"""
        print("🧪 Testing Slack connection...")
        success = self.send_message(
            text="✅ Fantasy Football Recap Bot connected successfully!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Fantasy Football Recap Bot connected successfully!*\n\nYou'll receive weekly recaps here automatically.",
                    },
                }
            ],
        )

        if success:
            print("✅ Test message sent successfully!")
        else:
            print("❌ Test message failed. Check your configuration.")

        return success


def main():
    """CLI for testing Slack integration"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Slack integration")
    parser.add_argument("--test", action="store_true", help="Send a test message")
    parser.add_argument("--week", type=int, help="Send recap for specific week")

    args = parser.parse_args()

    try:
        notifier = SlackNotifier()

        if args.test:
            notifier.test_connection()
        elif args.week:
            # Read the recap file
            recap_file = f"output/week-{args.week}-recap.md"
            if not os.path.exists(recap_file):
                print(f"❌ Recap file not found: {recap_file}")
                print("   Generate it first with: python scripts/example_generate_recap.py")
                exit(1)

            with open(recap_file, "r") as f:
                recap_content = f.read()

            notifier.send_recap(args.week, recap_content)
        else:
            print("Usage:")
            print("  Test connection: python -m src.slack_notifier --test")
            print("  Send recap: python -m src.slack_notifier --week 6")

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease set up your Slack credentials in .env file:")
        print("  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print("  OR")
        print("  SLACK_BOT_TOKEN=xoxb-your-bot-token")
        print("  SLACK_CHANNEL=#your-channel")
        exit(1)


if __name__ == "__main__":
    main()
