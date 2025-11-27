## Prerequisites

*   ADB installed and configured on your system.
*   An Android device or emulator connected to your computer.
*   Set resolution to 1080p in the emulator settings with aspect ratio 16:9.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/xdhiru/ark-curser
    cd ark-curser
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    *   **On Windows:**

        ```bash
        venv\Scripts\activate
        ```

    *   **On macOS and Linux:**

        ```bash
        source venv/bin/activate
        ```

4.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Configure ADB:**

    Ensure that ADB is properly configured and your device/emulator is connected. You might need to specify the device IP address in the `config/settings.yaml` file (default configuration is 127.0.0.1:5555 for BlueStacks).

2. **Modify config/settings.yaml for usage**

3.  **Run the script inside venv:**

    ```bash
    python main.py
    ```

