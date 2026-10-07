# Gremlin-Platforms R1

## Introduction

**Getting Help:** If you have issues running Gremlin or questions on how to
make certain things work, the best place to ask for help is in the
`#joystick-gremlin` channel on the [HOTAS Discord](https://discord.gg/hotas).

Gremlin-Platforms R1 configures joystick-like devices. It is built on Joystick Gremlin. It works with any device that appears as a joystick to Windows, including devices from different manufacturers and custom devices. It uses the virtual joysticks provided by vJoy to map physical inputs to virtual inputs and to apply transformations such as response curves. It also provides macros, modes, and Python scripting.

The main features are:

- Works with arbitrary joystick like devices
- User interface for common and some not so common configuration tasks
- Merging of multiple physical devices into a single virtual device
- Axis response curve and dead zone configuration
- Mapping of joystick inputs to keyboard and mouse inputs
- Powerful and flexible macro system
- Arbitrary number of modes with inheritance and customizable mode switching
- Conditional execution of configured actions
- Python scripting support for unlimited customization

Joystick Gremlin provides a graphical user interface which allows commonly performed tasks, such as input remapping, axis response curve setups, and macro recording to be performed easily. Functionality that is not accessible via the UI can be implemented through custom modules.

## Getting Started

For a list of dependencies and an overview of how to install and use Gremlin take a look at the [Manual](https://whitemagic.github.io/JoystickGremlin/).


## Contributing

If you want to contribute to Gremlin by implementing new features or fixing bugs, you will need a local development setup. The easiest way is described below.

### Development Setup

The easiest way to get all the required libraries installed for Gremlin development is via a virtual environment managed by [Poetry](https://python-poetry.org). Throughout this the assumption is that [VS Code](https://code.visualstudio.com/) is used and the appropriate Python plugins are installed.

### Installing Poetry

Abbreviated instructions from the [official documentation](https://python-poetry.org/docs/#installing-with-the-official-installer).

- Install a Gremlin compatible version of Python, such as 3.13.x
- Open a new Terminal / Powershell instance
- Run the command
  ```powershell
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
  ```
- Add the poetry executable to your PATH setting
  ```powershell
  [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Users\Lionel\AppData\Roaming\Python\Scripts", "User")
  ```
- Launch a new Terminal / Powershell instance and check if poetry can be found by running
  ````powershell
  poetry --version
  ````
- Add the Poetry plugin (`zeshuaro.vscode-python-poetry`) to VS Code
- Create a virtual environment and install required packages by running the `Poetry install packages` command (`Ctrl + Shift + P`) in VS Code

- Restart VS Code for the new environment to be picked up
- Select the newly created Poetry virtual environment as the project's interpreter

### HidHide when run from source

With HidHide control on and the Allow list in use, the program adds its own executable to HidHide's program list so it still sees hidden devices. Run from source, that executable is `python.exe` of the virtual environment, so every Python program run with that `python.exe` sees hidden devices too. This is accepted for source runs; the installed `gremlin_platforms.exe` only lets itself through.
