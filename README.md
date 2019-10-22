# ftrack
Scripts and Integrations for ftrack API

If you are on windows, you can deploy all content of the ftrack-connect directory at once by running the `sendToFtrack.exe` in the root directory.
Also, for Visual Studio Code, the "build" task is already configured, if you open this repository's workspace through `ftrack-connect-workspace.code-workspace`.


# ftrack-connect
This directory includes actions.
When running `sendToFtrack.exe`, everything from here is copied (overwrite!) to the ftrack-user directory.
Please note, that your plugin directory is not cleared before that (because you might have more than the content in here), so you might need to clean up your files/directories on your own from time to time.

# deploy-source
This directory is the source code for the `sendToFtrack.exe` app (.NET3)
