"""
commands/board.py — Bulletin board commands

Commands:
    subjects    — list posts on the board in this room
    write       — compose a new post
    erase <n>   — delete post #n (author or staff only)
    read board <n> — read a specific post
"""

from models import BulletinBoard
from datetime import timezone, datetime


def _get_board_or_error(character, conn, session):
    board = BulletinBoard.get_board_in_room(conn, character.location_id)
    if not board:
        session.send("There is no bulletin board here.\n")
    return board


def _format_age(created_at):
    now = datetime.now(timezone.utc)
    delta = now - created_at
    days = delta.days
    if days == 0:
        return "today"
    elif days == 1:
        return "1 day ago"
    else:
        return f"{days} days ago"


class SubjectsCommand:
    def execute(self, character, conn, args, session):
        board = _get_board_or_error(character, conn, session)
        if not board:
            return

        board_id, board_name, _ = board
        posts = BulletinBoard.get_posts(conn, board_id)

        if not posts:
            session.send(f"\n{board_name} has no messages.\n")
            return

        lines = [f"\n{board_name}"]
        lines.append("-" * len(board_name))
        lines.append("")

        for i, post in enumerate(posts, start=1):
            post_id, author_name, subject, created_at = post
            age = _format_age(created_at)
            lines.append(f"  [{i:>2}]  {subject:<40}  {author_name:<16}  {age}")

        lines.append("")
        session.send("\n".join(lines) + "\n")


class WriteCommand:
    def execute(self, character, conn, args, session):
        board = _get_board_or_error(character, conn, session)
        if not board:
            return

        board_id, board_name, _ = board

        session.send(f"\nWriting on: {board_name}\n Subject: \n")
        subject = (session.recv() or "").strip()

        if not subject:
            session.send("Cancelled. (No subject entered.)\n")
            return

        session.send("\nEnter your message. Type @ on a blank line when done.\n")
        session.send("(No editing once a line is submitted.)\n\n")

        lines = []
        while True:
            line = session.recv() or ""
            if line.strip() == "@":
                break
            lines.append(line)

        if not lines:
            session.send("Cancelled. (No message entered.)\n")
            return

        body = "\n".join(lines)

        BulletinBoard.create_post(
            conn,
            board_id,
            character.id,
            character.name,
            subject,
            body,
        )

        session.send(f"\nYour message has been posted to {board_name}.\n")


class EraseCommand:
    def execute(self, character, conn, args, session):
        if not args:
            session.send("Erase which post? (e.g. erase 3)\n")
            return

        try:
            post_number = int(args[0])
        except ValueError:
            session.send("That's not a valid post number.\n")
            return

        board = _get_board_or_error(character, conn, session)
        if not board:
            return

        board_id, board_name, _ = board

        post = BulletinBoard.get_post_by_number(conn, board_id, post_number)
        if not post:
            session.send(f"There is no post #{post_number} on {board_name}.\n")
            return

        post_id, author_id, author_name, subject, body, created_at = post

        if character.id != author_id and not character.is_staff:
            session.send("You can only erase your own posts.\n")
            return

        BulletinBoard.delete_post(conn, post_id)
        session.send(f"Post #{post_number} \"{subject}\" has been erased.\n")


class ReadCommand:
    def execute(self, character, conn, args, session):
        if len(args) < 2:
            session.send("Read what? (e.g. read board 3)\n")
            return

        target = args[0].lower()

        if target != "board":
            session.send("You can't read that.\n")
            return

        try:
            post_number = int(args[1])
        except ValueError:
            session.send("That's not a valid post number.\n")
            return

        board = _get_board_or_error(character, conn, session)
        if not board:
            return

        board_id, board_name, _ = board

        post = BulletinBoard.get_post_by_number(conn, board_id, post_number)
        if not post:
            session.send(f"There is no post #{post_number} on {board_name}.\n")
            return

        post_id, author_id, author_name, subject, body, created_at = post
        age = _format_age(created_at)

        lines = [
            f"\n{board_name} — Post #{post_number}",
            f"Subject : {subject}",
            f"Author  : {author_name}",
            f"Posted  : {age}",
            "-" * 40,
            body,
            "",
        ]
        session.send("\n".join(lines) + "\n")