Halloween version that is based on the wonderful work by [David Svitov](https://github.com/david-svitov/fishscanner), who created the original FishScanner and [Joshua Harsono](https://github.com/jharsono/fishscanner) who added support for HEIC images, live updates, improved background detection, and more. This version turns it into kid friendly halloween creatures flying in the night sky instead of fishes in an aquarium


## Installation (macOS)

```bash
git clone https://github.com/SamE090954/HalloweenScanner.git
cd HalloweenScanner
./setup.sh

# Important: Log out and log back in after installation
```

## How to Use

1. Print a template
   - Choose any template from `background/patterns/' except blank.pdf
   - Each template has special markers in the corners for detection

2. Draw your creature
   - Use any colors or designs you like
   - Keep your drawing inside the marked area
   - Make sure the corner markers stay visible

3. Add your creature
   - Take a photo of your drawing and save it to the `photos` folder
   - Supported formats: JPG and HEIC (iPhone photos)
   - The creature will appear automatically in the night sky!
   - Run the app: `./run.sh`

## Controls

- **Arrow Keys**: Use left and right arrow keys to switch between different sky scenes
- **ESC**: Exit the application


## Platform Compatibility

FishScanner is compatible with:
- macOS (both Apple Silicon and Intel)
- Windows
- Linux

### Platform-Specific Notes

#### macOS
- Works on both Apple Silicon (M1/M2) and Intel processors
- No additional configuration needed

#### Windows
- Requires OpenGL drivers (typically pre-installed)
- May need to install Microsoft Visual C++ Redistributable if not already present

#### Linux
- Requires OpenGL development libraries
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-opengl
  sudo apt-get install libglfw3
  ```

All core dependencies (numpy, OpenCV, PyOpenGL, etc.) are cross-platform compatible.

## Troubleshooting

Having issues? Check these common solutions:

1. **First time setup fails**
   - Make sure you're connected to the internet
   - Try running the commands in the [Manual Setup](#manual-setup) section

2. **App doesn't start**
   - Make sure you logged out and back in after installation
   - Try running `open -a XQuartz` manually

For detailed solutions to these and other issues, see our [Troubleshooting Guide](TROUBLESHOOTING.md).

## Manual Setup

If you prefer manual installation or the setup script fails:

1. Install system dependencies:
```bash
brew install glfw python@3.11 freeglut
brew install --cask xquartz
```

2. Set up Python:
```bash
python3.11 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

3. Configure environment:
```bash
echo "export DISPLAY=:0" >> ~/.zshrc
# Log out and log back in
```

## Project Structure

- `background/patterns/`: Fish templates for printing
- `photos/`: Place your scanned drawings here
- `engine/`: Core application code