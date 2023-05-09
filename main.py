"""MIT License

Copyright (c) 2023 stngularity

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

import os
import sys
import shutil
import re
from typing import Any, List, Tuple, Mapping, Optional

from rich.console import Console
from rich.theme import Theme
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# init params
console: Console = Console(theme=Theme(inherit=False))
print = console.print


def humonize(size: int) -> str:
    """:class:`str`: Humonizes size (in bytes)
    
    Parameters
    ----------
    size: :class:`int`
        The input size in bytes"""
    metrics: List[str] = ["bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    metric: int = 0
    final_size: float = size

    while final_size >= 1024 and metric < len(metrics) - 1:
        final_size = final_size / 1024
        metric += 1

    return f"{round(final_size, 2)} {metrics[metric]}"


def log(level: str, content: str) -> None:
    """Writes a log message to the console
    
    Parameters
    ----------
    level: :class:`str`
        The level of log

    content: :class:`str`
        The content of error message"""
    if level.lower() == "info":
        print(f"[blue]Info[/]       {content}")

    if level.lower() == "warn":
        print(f"[yellow]Warning[/]    {content}")

    if level.lower() == "error":
        print(f"[red]Error[/]      {content}")

    if level.lower() == "debug":
        print(f"[bright_black]Debug[/]      {content}")

    if level.lower() == "crit":
        print(f"[red bold]Critical[/]   {content}")
        exit(0)


def find_config() -> Mapping[str, Any]:
    """Mapping[:class:`str`, :class:`Any`]: Tries to find and load the project configuration"""
    if "bdproject" not in [re.sub(r"\.ya?ml", "", f) for f in os.listdir()]:
        log("crit", "Project configuration file not found. Please create it.")

    filename: str = [f for f in os.listdir() if f.startswith("bdproject")][0]
    if not filename.endswith((".yml", ".yaml")):
        log("crit", "The found project configuration file is not a YAML file.")

    try:
        with open(filename, "r", encoding="utf-8") as reader:
            data: Mapping[str, Any] = YAML().load(reader)

    except YAMLError:
        log("crit", "Failed to process project configuration.")

    else:
        if "type" not in data.keys():
            log("crit", "The required parameter \"type\" was not specified.")

        log("debug", "Found configuration file of BetterDiscord project")
        return data

    return {}


def find_betterdiscord() -> str:
    """:class:`str`: Tries to find the BetterDiscord folder"""
    platform: str = sys.platform
    folder: str = ""

    # User system is Windows
    if platform.startswith("win32"):
        appdata: Optional[str] = os.environ.get("AppData")
        folder = f"{appdata}\\BetterDiscord"

    # User system is MacOS
    if platform.startswith("darwin"):
        folder = "~/Library/Application Support/BetterDiscord"

    # User system is Linux
    if platform.startswith("linux"):
        folder = "~/.config/BetterDiscord/"

    if not os.path.exists(folder):
        log("crit", "Couldn't find BetterDiscord folder!")

    return folder


def get_metadata(input: str) -> Tuple[str, Mapping[str, Any]]:
    """Mapping[:class:`str`, :class:`Any`]: Tries to find and parse project metadata
    
    Parameters
    ----------
    input: :class:`str`
        The code (content) of input file"""
    output: Mapping[str, Any] = {}

    metadata: List[str] = re.findall(r"/\*\*.*\*/", input, re.S)
    if len(metadata) < 1:
        log("crit", "Could not find metadata!")

    for key, value in re.findall(r"@([a-zA-Z]+) (.*)", metadata[0]):
        output[key] = value

    return metadata[0], output


def prepare(input: str) -> str:
    """:class:`str`: Prepares input code
    
    Parameters
    ----------
    input: :class:`str`
        The code (content) of input file"""
    output: str = input
    imports: List[str] = re.findall(r"@import url\(\"(.+)\"\);", input)
    for _import in imports:
        name: str = os.path.join(os.path.curdir, _import.strip("/"))
        with open(name, "r", encoding="utf8") as reader:
            output = output.replace(f"@import url(\"{_import}\");", reader.read())

    return output


def minify(input: str, mode: str) -> str:
    """:class:`str`: Minimizes given code (content) of input file
    
    Parameters
    ----------
    input: :class:`str`
        The code (content) of input file
        
    mode: :class:`str`
        The minify mode (`theme` or `plugin`)"""
    if mode == "theme":
        output: str = ""

        lines: List[str] = re.split(r" *\n *", input)
        for line in lines:
            output += line.strip()

        output = re.sub(r"(/\*.*\*/)", "", output)
        output = re.sub(r" *\{", "{", output)
        output = re.sub(r": *", ":", output)
        output = re.sub(r" *, *", ",", output)
        output = re.sub(r" *!important", "!important", output)
        output = output.replace(";}", "}")
        return output

    return input


def get_name(config: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    """:class:`str`: Gets the name of output file
    
    Parameters
    ----------
    config: Mapping[:class:`str`, :class:`Any`]
        The configuration of project
        
    metadata: Mapping[:class:`str`, :class:`Any`]
        The metadata of project"""
    original: str = config.get("output", {}).get("name", "$name-$version.$type.$ext")
    output: str = original
    for placeholder in re.findall(r"\$([a-z]+)", original):
        if placeholder not in ["name", "version", "author", "type", "ext"]:
            continue

        output = output.replace(f"${placeholder}", {
            "name": metadata["name"].replace(" ", ""),
            "version": metadata["version"],
            "author": metadata["author"],
            "type": config["type"],
            "ext": "css" if config["type"] == "theme" else "js"
        }[placeholder])

    return output


def main() -> None:
    """A entrypoint of this program"""
    config: Mapping[str, Any] = find_config()
    type: str = config["type"]

    # Get input file content
    filename: str = config.get("mainFilename", type)
    input_file: str = f"{filename}.{'css' if type == 'theme' else 'js'}"
    with open(input_file, "r", encoding="utf-8") as reader:
        input: str = prepare(reader.read())
        size: int = len(input)

    log("debug", f"Found [green]{input_file}[/] file with size of [green]{humonize(size)}[/]")

    # Find the metadata of project
    mdcomment, metadata = get_metadata(input)
    name: str = metadata["name"]
    version: str = metadata["version"]
    author: str = metadata["author"]
    log("debug", f"Found [green]{name} v{version}[/] {type} by [green]{author}[/]")

    # If "doMimize" option is true,
    # then minify output
    content: str = input
    if config.get("options", {}).get("doMimize", False):
        content = minify(input, type)
        log("info", "The content of project is minified")

    # Save output
    name: str = get_name(config, metadata)
    folder: str = os.path.join(os.getcwd(), config.get("output", {}).get("folder", ""))
    os.makedirs(folder, exist_ok=True)

    fullpath: str = os.path.join(folder, name)
    with open(fullpath, "w", encoding="utf8") as writer:
        output_size: int = writer.write(mdcomment+"\n"+content)

    log("info", f"Generated file [green]{name}[/] with size of [green]{humonize(output_size)}[/]")
    log("debug", f"Output size is [green]{humonize(size-output_size)}[/] less than the input")

    # If "autoMoveToBetterDiscordFolder" option is true,
    # then copy the output to BetterDiscord folder
    if config.get("options", {}).get("autoMoveToBetterDiscordFolder", False):
        bdfolder: str = find_betterdiscord()
        log("debug", f"BetterDiscord is located by [green]{bdfolder}[/] folder")
        shutil.copy(fullpath, os.path.join(bdfolder, type+"s", name))
        log("info", f"Generated {type} copied to BetterDiscord folder.")
        log("info", "[green]Go to Discord to see result[/]")

if __name__ == "__main__":
    main()
