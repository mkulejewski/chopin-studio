# Agent instructions

## Browser testing must not interrupt the user's work

- Never use the user's open Chrome/Chromium windows, tabs, or profiles for testing. Do not navigate, focus, resize, close, or change zoom or fullscreen in those sessions.
- Do not use connected-browser or in-app browser automation to test this project when it can affect the user's desktop browser. Interact with the user's browser only when the user specifically asks for that interaction.
- Run UI tests in a separate **headless Playwright browser process**, with Playwright's fresh temporary profile and isolated browser contexts. Never attach to the user's browser through CDP or reuse their profile.
- Configure resolution and fullscreen checks only inside that isolated test browser. Include **1920×1080** for this user's Full HD display; use smaller viewports as additional responsive checks.
- Use a dedicated loopback test port, temporary application data and state directories, and `CHOPIN_NO_HARDWARE=1`. Never reuse the production server or access the physical piano/microphone during automated tests.
- Inspect saved screenshots, traces, DOM bounds, and test results instead of manipulating a live browser. Do not run headed tests unless the user explicitly requests a separate visible test browser.
