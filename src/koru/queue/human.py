"""Human interaction utilities for the planfile queue."""


def default_human_prompt(prompt: str, ticket_id: str) -> str | None:
    """Read a multi-line human answer from stdin.

    Returns the trimmed answer, or ``None`` if the user cancelled
    (Ctrl-C) or submitted an empty response. Ctrl-D submits.
    """
    print()
    print(f"📝 {ticket_id} — human input needed")
    print("─" * 60)
    print(prompt)
    print("─" * 60)
    print("Type your answer (Ctrl-D to submit, Ctrl-C to cancel):")
    lines: list[str] = []
    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\n[cancelled — ticket left untouched]")
        return None
    answer = "\n".join(lines).strip()
    if not answer:
        print("[empty answer — ticket left untouched]")
        return None
    return answer
