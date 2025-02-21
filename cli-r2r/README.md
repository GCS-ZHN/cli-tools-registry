# R2R SFTP Bridge

A secure and efficient CLI tool for transferring files between remote servers using SFTP with SSH config integration.

## Features

- 🔄 Direct server-to-server transfers
- 🔑 Supports both password and key-based authentication
- ⚡ Stream mode for large files (default)
- 📁 Buffer mode for small files
- 🔧 Automatic SSH config resolution
- 📊 Transfer progress visualization
- 🔒 Encrypted connections using Paramiko

## Commands

### `bridge` command options:
| Option | Description |
|--------|-------------|
| `--username-src` | Source server username override |
| `--username-dst` | Destination server username override |
| `--port-src` | Source server SSH port (default: 22) |
| `--port-dst` | Destination server SSH port (default: 22) |
| `--identity-src` | Path to source server private key |
| `--identity-dst` | Path to destination server private key |
| `--stream/--buffer` | Transfer mode (default: stream) |


## TODO
- [ ] Implement resume support for interrupted transfers
- [ ] Add unit tests for `sftp_connection` context manager
- [ ] Improve error handling and logging
- [ ] Add support for parallel transfers
- [ ] Enhance CLI with additional options (e.g., bandwidth limit)
- [ ] Create detailed user documentation
- [ ] Add support for SCP protocol
- [ ] Implement configuration file for default settings
- [ ] Optimize performance for high-latency networks



