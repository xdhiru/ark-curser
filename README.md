## Prerequisites

*   ADB installed and configured on your system:
    ```
    https://developer.android.com/tools/releases/platform-tools
    ```
*   An Android emulator
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

## Points to Note (IMPORTANT) 

1. **Personal Project Disclaimer**
   This project was developed as a personal experiment and may **not work** for everyone on the first or second try.

   * If issues occur, check the logs:

     ```
     logs/ark_curser.log
     ```

2. **Potential Points of Failure**

   * **Base Icon Template:** The `"Base"` icon used to enter the base on the home screen relies on the **default dark theme**. Using a different theme will cause it to fail. 
   ```
   Fix: Define your own Base icon template using the steps mentioned below.
   ```
   * **Hardcoded Delays:** Many `time.sleep()` calls are used for taps, swipes, and loading waits. These depend on your system’s response times. You may need to **adjust these timers** to prevent broken interactions (e.g., trading posts not found if the base takes longer to load).
   ```
   Fix: Go through the source code and adjust them.
   ```

3. **Trading Post Worker Swapping**

   * Worker swapping uses worker name and category templates for matching and speeding-up swaps.
   * To add your own workers:

     1. Place the worker's name template PNG in the `Templates/` directory.
     2. Place the worker's category if it does not already exist.
     3. Update the dictionary in `tasks/handle_trading_posts.py` with the new worker’s details.

