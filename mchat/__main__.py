import argparse
from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install
from minecraft.networking.packets.clientbound.play import ChatMessagePacket
from minecraft.networking.connection import Connection
from minecraft.authentication import AuthenticationToken
from minecraft.exceptions import YggdrasilError
from minecraft.networking.packets import serverbound
from minecraft.networking.packets import clientbound
from minecraft import SUPPORTED_MINECRAFT_VERSIONS
import getpass
import json
import socket

# Pretty-print console object
install()
console = Console()


def incomingChatHandler(packet):

    # Deserialize JSON data
    packet_json: dict
    if type(packet.json_data) == str:
        packet_json = json.loads(packet.json_data)
    else:
        packet_json = packet.json_data

    # String segments
    str_segs = []

    # Handle every line of "extras"
    for extra in packet_json["extra"]:

        # Get the color
        color: str = extra.get("color", "white")

        # Get formatting extras
        bold: bool = extra.get("bold", False)
        italic: bool = extra.get("italic", False)
        underlined: bool = extra.get("underlined", False)
        strikethrough: bool = extra.get("strikethrough", False)
        obfuscated: bool = extra.get("obfuscated", False)

        # Get the actual text
        text: str = extra.get("text", "")

        # Build tags list
        tags = []

        if bold:
            tags.append("bold")
        if italic:
            tags.append("italic")
        if underlined:
            tags.append("underline")
        if strikethrough:
            tags.append("strike")

        # Add a final seperator
        if len(tags) > 0:
            tags.append(" ")

        # Build closing tags block
        closing_block = "[/]" if len(tags) else ""

        # Handle formatting
        str_segs.append(
            "[{tags}{color}]{text}{closing_block}".format(tags=" ".join(tags), color=color, text=text, closing_block=closing_block))

    # Build the chat line
    chat_line = " ".join(str_segs)

    console.print(chat_line)


def main() -> int:

    # Handle program arguments
    ap = argparse.ArgumentParser(
        prog="mchat", description="A console chat client for most Minecraft server versions")
    ap.add_argument("server_address", help="IP address of a Minecraft server")
    ap.add_argument("-p", "--port", help="Minecraft server port (default: %(default)s)",
                    type=int, default=25565)
    ap.add_argument("-u", "--username", help="Minecraft username or email")
    ap.add_argument("-v", "--version", help="Client -> Server protocol version to use (default: %(default)s)",
                    default="1.16.4")
    args = ap.parse_args()

    # Verify server version to keep the terminal looking clean
    if args.version not in SUPPORTED_MINECRAFT_VERSIONS.keys():
        console.print(
            f"[bold yellow]{args.version} is not a valid Minecraft version. Versions from {list(SUPPORTED_MINECRAFT_VERSIONS.keys())[0]} to {list(SUPPORTED_MINECRAFT_VERSIONS.keys())[-1]} are allowed.")
        return 1

    # Do authentication
    if not args.username:
        username = Prompt.ask("Username or email")
    else:
        username = args.username

    password = getpass.getpass("Password: ")
    console.print(f"[bright_black]Loaded authentication information")

    # Determine the actual protocol version number
    protocol_version_num = SUPPORTED_MINECRAFT_VERSIONS[args.version]
    console.print(
        f"[bright_black]Selecting protocol version {protocol_version_num}")

    # Authenticate with Mojang
    auth_token = AuthenticationToken()
    console.print(f"[bright_black]Contacting Yggdrasil...")

    try:
        auth_token.authenticate(username, password)
    except YggdrasilError as e:
        console.print(f"[bold red]Failed to authenticate Minecraft session")
        return 1

    # Open a connection
    server_connection = Connection(
        args.server_address, args.port, auth_token, allowed_versions=[args.version])

    try:
        server_connection.connect()
    except:
        console.print(f"[bold red]Could not connect to server")
        return 1

    # Set up an incoming chat handler
    server_connection.register_packet_listener(
        incomingChatHandler, ChatMessagePacket)
    console.print(f"[bright_black]Listen to incoming chat packets")

    # Set up input loop
    console.print(
        "All further inputs will be sent to server chat. Press CTRL+C to stop")
    try:
        while True:

            # Get a line from the user
            chat_message = console.input()

            # Send the chat message
            packet = serverbound.play.ChatPacket()
            packet.message = chat_message
            server_connection.write_packet(packet)

    except KeyboardInterrupt as e:
        print("\rGoodbye.", end="")

    return 0


if __name__ == "__main__":
    exit(main())
