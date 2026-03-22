"""CLI commands for Diagram Forge."""

import sys
import json
import argparse
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger("diagram_forge.cli")

BASE_URL = "http://localhost:8000"


def configure_logging(verbose: bool = False) -> None:
    """Configure basic logging for CLI."""
    import logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=level,
        stream=sys.stderr,
    )


def load_config() -> dict:
    """Load CLI configuration from config file or env."""
    api_key = (
        Path("~/.config/diagram-forge/config.toml").expanduser().read_text().split("api_key=")[1].split("\n")[0]
        if Path("~/.config/diagram-forge/config.toml").expanduser().exists()
        else None
    )
    env_key = Path("/dev/stdin").read_text() if False else None  # placeholder
    api_key = api_key or __import__("os").environ.get("DIAGRAM_FORGE_API_KEY", "")
    return {"api_key": api_key}


def do_generate(args: argparse.Namespace) -> int:
    """Handle 'df generate' command."""
    configure_logging(args.verbose)

    api_key = args.api_key or __import__("os").environ.get("DIAGRAM_FORGE_API_KEY", "")
    if not api_key:
        print("ERROR: API key required. Set DIAGRAM_FORGE_API_KEY env or use --api-key", file=sys.stderr)
        return 1

    base_url = args.base_url or __import__("os").environ.get("DIAGRAM_FORGE_BASE_URL", BASE_URL)

    # Build request
    text = args.text
    if args.input_file:
        text = Path(args.input_file).read_text()

    body = {
        "text": text,
        "diagram_type": args.type,
    }

    # Start generation
    headers = {"X-API-Key": api_key}
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        try:
            resp = client.post("/v1/generate/text", json=body, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"ERROR: {e.response.status_code}: {e.response.text}", file=sys.stderr)
            return 1
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to {base_url}. Is the server running?", file=sys.stderr)
            return 1

    result = resp.json()
    job_id = result["job_id"]
    poll_url = result.get("poll_url", f"/v1/jobs/{job_id}")

    print(f"Job created: {job_id}", file=sys.stderr)

    # Poll for completion
    print("Generating...", file=sys.stderr, end="", flush=True)
    import time
    for i in range(60):  # 60 attempts, ~2s each = 2min timeout
        time.sleep(2)
        try:
            status_resp = client.get(poll_url, headers=headers)
            status_resp.raise_for_status()
            status_data = status_resp.json()

            status_val = status_data.get("status", "unknown")
            print(f"\n  Status: {status_val}", file=sys.stderr, end="", flush=True)

            if status_val == "completed":
                print(file=sys.stderr)
                break
            elif status_val == "failed":
                print(file=sys.stderr)
                print(f"ERROR: Job failed: {status_data.get('error_message', 'Unknown error')}", file=sys.stderr)
                return 1
        except httpx.HTTPStatusError as e:
            print(f"\nERROR polling: {e}", file=sys.stderr)
            return 1

        print(".", file=sys.stderr, end="", flush=True)
    else:
        print("TIMEOUT: Job did not complete in 120 seconds", file=sys.stderr)
        return 1

    # Download result
    output_format = args.format or "excalidraw"
    download_url = f"/v1/jobs/{job_id}/download/{output_format}"

    try:
        dl_resp = client.get(download_url, headers=headers)
        dl_resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"ERROR downloading: {e}", file=sys.stderr)
        return 1

    # Write output
    if args.output:
        output_path = Path(args.output)
    else:
        suffix = ".excalidraw.json" if output_format == "excalidraw" else f".{output_format}"
        output_path = Path(f"diagram{job_id[:8]}{suffix}")

    output_path.write_bytes(dl_resp.content)
    print(f"Diagram saved to: {output_path}")
    return 0


def do_health(args: argparse.Namespace) -> int:
    """Handle 'df ping' / health check command."""
    base_url = args.base_url or __import__("os").environ.get("DIAGRAM_FORGE_BASE_URL", BASE_URL)
    try:
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            resp = client.get("/v1/health")
            resp.raise_for_status()
            print(f"OK: {resp.json()}")
            return 0
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to {base_url}", file=sys.stderr)
        return 1


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="df", description="Diagram Forge CLI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--api-key", help="API key (or set DIAGRAM_FORGE_API_KEY)")
    parser.add_argument("--base-url", help=f"API base URL (default: {BASE_URL})")

    subparsers = parser.add_subparsers(dest="command")

    # df generate
    gen = subparsers.add_parser("generate", help="Generate a diagram")
    gen.add_argument("--text", "-t", help="Text description of the diagram")
    gen.add_argument("--input-file", "-f", type=Path, help="Read text from file")
    gen.add_argument("--type", default="architecture",
        choices=["architecture", "sequence", "flowchart"],
        help="Diagram type")
    gen.add_argument("--format", "-o", default="excalidraw",
        choices=["excalidraw", "drawio", "svg"],
        help="Output format")
    gen.add_argument("--output", "-O", type=Path, help="Output file path")

    # df ping / health
    ping = subparsers.add_parser("ping", help="Check server health")
    ping.add_argument("--watch", action="store_true", help="Watch continuously")

    # df docs
    docs = subparsers.add_parser("docs", help="Open API documentation")
    docs.add_argument("--open", action="store_true", help="Open in browser")

    args = parser.parse_args()

    if args.command == "generate":
        return do_generate(args)
    elif args.command == "ping":
        return do_health(args)
    elif args.command == "docs":
        url = (args.base_url or BASE_URL) + "/docs"
        print(f"API docs: {url}")
        if args.open:
            import webbrowser
            webbrowser.open(url)
        return 0
    else:
        parser.print_help()
        return 0
