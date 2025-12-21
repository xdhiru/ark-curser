## Features

*   Swap Proviso, Tequila and Quartz into trading posts as an order is about to finish.
*   Swap them out and swap the original workers back in when that order has finished and a new one has started.
*   Check for login session expiry before the swapping procedure.
*   If it had expired, initiate a re-login.
*   If there are two swap tasks within a small time interval (`curse_conflict_threshold` in `config/settings.yaml`), use drones to immediately finish the first one.
*   Adaptively optimize the wait and delay timings (`utils/adaptive_waits.py`) based on the in-game response times.
*   Save these optimized timings (in `config/adaptive_waits.pkl`) for future usage.

## Limitations

*   The whole project was done/tested with level 3 Trading Posts, so it may or may not work for level 2. Most probably won't.


## Prerequisites

*   ADB installed and configured on your system:
    ```
    https://developer.android.com/tools/releases/platform-tools
    ```
*   An android emulator
*   Resolution set to 1080p in the emulator settings with aspect ratio 16:9

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
    or if that fails,
    ```bash
    python3 main.py
    ```

## Points to Note (IMPORTANT) 

1. **Personal Project Disclaimer:**
   This project was developed as an experiment and may **not work** for others at once.

   * If issues occur, check the logs:

     ```
     logs/ark_curser.log
     ```

2. **Potential Points of Failure**

   1. **Home Screen Themes/Base Icon Template:** The appearance of "Base" icon on the game's home screen changes based on the applied theme. This icon is essential in order to enter the base. By default, this project uses the game's **dark theme** icons for its templates. Using a different theme will break it. 
   
        **Fix:** Create the correct base-icon template for the applied theme (and for the other icons wherever applicable):
        ```
        Templates/base-icon.png
        ```
        
        
   2. **Hardcoded Delays:** Despite having an adaptive optimizer mechanism for the wait timers, many `static_wait` calls are used for waits during interactions and loading screens which shouldn't be optimized. These depend on your system’s response times. 
    
        **Fix:** **Adjust those wait timers** in 
        ```
        utils/adaptive_waits.py
        ``` 
        Now to load the changed timings freshly, remember to delete the save file containing the optimized timings from earlier:
        ```
        config/adaptive_waits.pkl
        ``` 

   3. Many more such points beyond the scope of this readme.
   

3. **Trading Post Worker Swapping**

   * Worker swapping uses worker name and category templates for matching and speeding-up swaps.
   * To add your own workers:

     1. Place the worker's name template PNG in the `Templates/` directory.
     2. Place the worker's category icon if it does not already exist.
     3. Update the dictionary in `tasks/handle_trading_posts.py` with the new worker’s details.