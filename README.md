# Cli Tools Registry

This repository contains a collection of command-line interface (CLI) tools designed to assist with various tasks. Each tool is maintained in its own directory and includes its own documentation and configuration files.

## How to Submit a New CLI Tool

To submit a new CLI tool to this registry, follow these steps:

1. **Fork the Repository**: Start by forking the current repository to your own GitHub account.

2. **Create a New Directory**: Add a new directory named `cli-XXX` (replace `XXX` with the name of your CLI tool).

3. **Add Your Python Project**: Inside the `cli-XXX` directory, create a complete Python project based on `pyproject.toml`. Ensure that the `pyproject.toml` file includes the following fields:
    ```toml
    [project]
    name = "cli-XXX"
    version = "0.1.0"
    description = "A brief description of your CLI tool"
    authors = [{"name": "Your Name", "email": "your.email@example.com"}]
    ```

4. **Specify the Entry Point**: In the `pyproject.toml` file, specify the entry point for your CLI tool as follows:
    ```toml
    [project.scripts]
    XXX = "cli_XXX.cli:main"
    ```

5. **Submit a Pull Request**: Once you have added your CLI tool, submit a pull request to the main repository. Make sure to include a detailed description of your tool and its functionality.

By following these steps, you can contribute your CLI tool to the registry and make it available for others to use.


