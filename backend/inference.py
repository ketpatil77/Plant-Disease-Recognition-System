from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image, UnidentifiedImageError

from .metadata import build_prediction_payload
from .model import CNN, IDX_TO_CLASSES, NUM_CLASSES

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PredictionError(RuntimeError):
    """Base exception for inference failures."""


class UnsupportedFileError(PredictionError):
    """Raised when a file extension is not supported."""


class InvalidImageError(PredictionError):
    """Raised when the uploaded file is not a readable image."""


class PlantDiseaseService:
    """
    Plant disease detection inference service.
    Handles model loading, image validation, preprocessing, and inference.
    
    Model expects 224x224 RGB images normalized to [0,1] range.
    Outputs probabilities across 39 disease/healthy classes.
    """
    def __init__(self, model_path: Path | str, device: str = "cpu"):
        """
        Initialize the plant disease detection service.
        Args:
            model_path: Path to PyTorch model state dict (.pt file)
            device: Device to use for inference ('cpu' or 'cuda')
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If model fails to load
        """
        self.model_path = Path(model_path)
        self.device = torch.device(device)
        self.model = self._load_model()

    def _load_model(self):
        """
        Load CNN model from disk and prepare for inference.
        Returns:
            Loaded CNN model in eval mode on specified device
        Raises:
            FileNotFoundError: If model file not found
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        model = CNN(NUM_CLASSES)
        state_dict = torch.load(self.model_path, map_location=self.device)
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()
        return model

    def validate_image(self, image_path: Path):
        """
        Validate that uploaded file is a readable image with supported format.
        Args:
            image_path: Path to image file
        Raises:
            UnsupportedFileError: If file extension not in {.jpg, .jpeg, .png, .webp}
            InvalidImageError: If file is not a valid readable image
        """
        if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileError("असमर्थित फाइल प्रकार. कृपया JPEG, PNG किंवा WEBP प्रतिमा अपलोड करा.")

        try:
            with Image.open(image_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidImageError("अपलोड केलेली फाइल वैध प्रतिमा नाही किंवा ती खराब आहे.") from exc

    def preprocess(self, image_path: Path):
        """
        Load image from disk and preprocess for model inference.
        Converts to RGB, resizes to 224x224, normalizes to [0,1].
        Args:
            image_path: Path to image file
        Returns:
            PyTorch tensor of shape (1, 3, 224, 224) ready for model input
        Raises:
            InvalidImageError: If image cannot be read or processed
        """
        try:
            with Image.open(image_path) as image:
                image = image.convert("RGB")
                image = image.resize((224, 224), Image.Resampling.BILINEAR)
                # Convert PIL image to tensor without numpy dependency
                width, height = image.size
                pixel_list = list(image.getdata())
                tensor = torch.FloatTensor(pixel_list)
                tensor = tensor.view(height, width, 3) / 255.0
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidImageError("अपलोड केलेली फाइल वैध प्रतिमा नाही किंवा ती खराब आहे.") from exc

        # Rearrange dimensions: (H, W, C) -> (C, H, W) and add batch dimension
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        return tensor.to(self.device)

    def predict_path(self, image_path: Path | str, *, image_url: str):
        """
        Predict plant disease from image file.
        Args:
            image_path: Path to plant image file
            image_url: URL of uploaded image for response payload
        Returns:
            Dictionary with class_name, confidence, disease_info, and image_url
        Raises:
            UnsupportedFileError: If file type not supported
            InvalidImageError: If image is not readable
        """
        image_path = Path(image_path)
        self.validate_image(image_path)
        inputs = self.preprocess(image_path)

        with torch.no_grad():
            logits = self.model(inputs)
            probabilities = torch.softmax(logits, dim=1)
            index = int(torch.argmax(logits, dim=1).item())
            confidence = float(probabilities[0, index].item() * 100)

        class_name = IDX_TO_CLASSES[index]
        return build_prediction_payload(class_name, confidence, image_url)
