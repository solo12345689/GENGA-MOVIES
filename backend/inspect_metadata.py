import asyncio
from moviebox_api.models import DownloadableFilesMetadata
from pydantic import BaseModel

def inspect_model(model_class):
    print(f"Inspecting {model_class.__name__}:")
    if hasattr(model_class, 'model_fields'):
        for name, field in model_class.model_fields.items():
            print(f"  - {name}: {field.annotation}")
    elif hasattr(model_class, '__fields__'):
        for name, field in model_class.__fields__.items():
            print(f"  - {name}: {field.outer_type_}")
    else:
        print("  Could not find fields")

if __name__ == "__main__":
    from moviebox_api.models import DownloadableFilesMetadata, CaptionFileMetadata, SearchResultsItem, MediaFileMetadata
    for model in [DownloadableFilesMetadata, CaptionFileMetadata, SearchResultsItem, MediaFileMetadata]:
        inspect_model(model)
        print("-" * 20)
