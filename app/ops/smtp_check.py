from __future__ import annotations

import argparse
import smtplib
import sys

from app.connectors.email import SmtpEmailSender


def verify_smtp(*, send_test: bool, to_email: str | None) -> int:
    try:
        sender = SmtpEmailSender()
    except Exception as exc:
        print(f"SMTP configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        with smtplib.SMTP(sender.host, sender.port, timeout=15) as smtp:
            smtp.ehlo()
            if sender.use_tls:
                smtp.starttls()
                smtp.ehlo()
            if sender.username and sender.password:
                smtp.login(sender.username, sender.password)
            if send_test:
                if not to_email:
                    print("--to is required when --send-test is used.", file=sys.stderr)
                    return 1
    except Exception as exc:
        print(f"SMTP connectivity check failed: {exc}", file=sys.stderr)
        return 1

    if send_test:
        try:
            sender.send(
                to_email=to_email or sender.from_email,
                subject="Portfolio Optimization SMTP smoke test",
                body="This is a deployment-time SMTP smoke test.",
            )
        except Exception as exc:
            print(f"SMTP test email failed: {exc}", file=sys.stderr)
            return 1

    print("SMTP check passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify SMTP configuration and connectivity.")
    parser.add_argument("--send-test", action="store_true", help="Send a test email after authenticating.")
    parser.add_argument("--to", help="Destination email for --send-test.")
    args = parser.parse_args(argv)
    return verify_smtp(send_test=args.send_test, to_email=args.to)


if __name__ == "__main__":
    raise SystemExit(main())
