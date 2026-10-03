from functools import lru_cache

from PIL import Image, ImageOps


@lru_cache(maxsize=1)
def load_model(path: str, classes: tuple):
    import torch
    from torchvision.models import ResNet18_Weights, resnet18

    model = resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
    # Only locally trained state dictionaries, never untrusted pickled model objects.
    model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    model.eval()
    return model, ResNet18_Weights.DEFAULT.transforms()


def predict(path, classes, image_path):
    import torch

    model, transform = load_model(str(path), tuple(classes))
    with Image.open(image_path) as image:
        tensor = transform(ImageOps.exif_transpose(image).convert("RGB")).unsqueeze(0)
    with torch.inference_mode():
        values = model(tensor).softmax(dim=1)[0]
    index = int(values.argmax())
    return classes[index], float(values[index])
