from moviebox_api.models import SearchResultsItem
from moviebox_api.extractor.models.json import SubjectModel, SubjectTrailerModel, ItemJsonDetailsModel
import pydantic

print(f"SearchResultsItem schema: {SearchResultsItem.model_json_schema()}")
print(f"ItemJsonDetailsModel schema: {ItemJsonDetailsModel.model_json_schema()}")

# Test if we can create a SearchResultsItem from a dict
dummy_data = {
    "id": "123",
    "title": "Test Movie",
    "cover": {"url": "http://example.com/poster.jpg"},
    "releaseDate": "2023-01-01"
}

try:
    item = SearchResultsItem(**dummy_data)
    print("Successfully created SearchResultsItem")
except Exception as e:
    print(f"Failed to create SearchResultsItem: {e}")
