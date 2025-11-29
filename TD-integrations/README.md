# External Integrations Guide

This folder contains external integration tools for TouchDesigner and MCP (Model Context Protocol).
These features are optional and decoupled from the main application.

## 1. TouchDesigner Integration

This system allows sending real-time tracking data (skeleton, face, bbox) from Python to TouchDesigner via OSC (Open Sound Control).

### Files
- `td_transmitter.py`: The Python class responsible for sending OSC messages.
- `td_parse_split_packets.py`: A Python script to be used **inside TouchDesigner** (in a Script DAT) to parse the incoming data.
- `TOUCHDESIGNER_GUIDE.md`: Detailed setup instructions for TouchDesigner operators.

### How to Use
1.  **Enable in Python**:
    To re-enable transmission in the main app, you need to:
    - Move `td_transmitter.py` back to the root directory.
    - Edit `person_analysis.py` and set `TD_AVAILABLE = True`.
    - Ensure `python-osc` is installed: `pip install python-osc`

2.  **Setup TouchDesigner**:
    - Create an **OSC In CHOP**. Set port to `7000` (default).
    - Connect it to a **Script DAT**.
    - Paste the content of `td_parse_split_packets.py` into the Script DAT.
    - The Script DAT will output a table with parsed person data (id, x, y, etc.).

---

## 2. MCP (Model Context Protocol) Integration

This project includes a local MCP server implementation to allow AI assistants (like Cursor/Claude) to interact with the system state or external tools.

### Files
- `td_mcp/`: Contains the MCP server source code.
- `MCP_GUIDE.md`: Detailed setup guide for configuring Claude Desktop or Cursor to use this MCP server.

### How to Use
1.  **Install Dependencies**:
    Inside `td_mcp/modules/td_server`, run `pip install -r requirements.txt`.

2.  **Start Server**:
    Run `python td_mcp/modules/mcp_webserver_script.py`.

3.  **Connect Cursor/Claude**:
    Update your `claude_desktop_config.json` to point to this local server (see `MCP_GUIDE.md` for details).


