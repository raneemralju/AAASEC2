from fastmcp import FastMCP


mcp = FastMCP("Raneem Tools")


@mcp.tool
def calculate(expression: str) -> float:
    """Evaluate a basic arithmetic expression, e.g. '2 * (3 + 4) ** 2'."""
    allowed = set("0123456789+-*/(). ")
    if not all(char in allowed for char in expression):
        raise ValueError("Expression contains unsupported characters")

    return float(eval(expression, {"__builtins__": {}}, {}))


@mcp.tool
def word_stats(text: str) -> dict:
    """Return basic statistics about the words in a text."""
    words = text.split()

    return {
        "word_count": len(words),
        "character_count": len(text),
        "unique_word_count": len(set(words)),
    }


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8001,
    )