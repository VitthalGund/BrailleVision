# BrailleVision Model Information

This directory holds the detection model weights for resolving Braille dots.

## Model Configuration

- **Target Model Architecture**: YOLOv8n (Nano) Object Detector
- **Classes**: 1 (`dot` - single raised embossed bump)
- **Input Dimensions**: 640x640 pixels

## Files
- `best.pt`: PyTorch weights checkpoint (placed here after training)
- `model.onnx`: Exported ONNX format weight file for CPU deployment edge execution
- `model_info.md`: This file

## Robust Fallback Engine

If no custom YOLOv8 weight file (`best.pt` or `model.onnx`) is found inside this directory, the inference pipeline automatically activates the **OpenCV Fallback Blob Detector** (`cv2.SimpleBlobDetector`). This fallback is pre-configured with parameters tuned specifically for physical circular Braille dots:
- Area constraints: 20 to 500 pixels
- Circularity threshold: >= 0.60
- Convexity threshold: >= 0.80
- Inertia ratio: >= 0.50

This ensures the end-to-end API, client-side camera scanning, and debugger overlay interfaces remain fully testable out-of-the-box.
