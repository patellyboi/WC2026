from database import leaderboard as load_leaderboard


def format_leaderboard(conn):
    rows = load_leaderboard(conn)
    lines = ["LEADERBOARD", ""]
    for index, row in enumerate(rows, start=1):
        lines.append(f"{index}. {row['name']:<8} {row['points']:>3}")
    return "\n".join(lines)
