"""
Debug script to check what the MovieBox API returns for homepage items
"""
import asyncio
import httpx
from moviebox_api import Search, SubjectType
import json

async def test_homepage_item():
    session = httpx.AsyncClient(verify=False, timeout=30.0)
    
    # Test with "Classroom of the Elite" - a known anime from homepage
    query = "Classroom of the Elite"
    
    print(f"\n{'='*60}")
    print(f"Testing: {query}")
    print(f"{'='*60}\n")
    
    # Search for it
    search_instance = Search(session=session, query=query, subject_type=SubjectType.ALL)
    results = await search_instance.get_content_model()
    
    if not results.items:
        print("❌ No results found")
        return
    
    item = results.items[0]
    print(f"✓ Found: {item.title}")
    print(f"  ID: {getattr(item, 'id', 'N/A')}")
    print(f"  SubjectID: {getattr(item, 'subjectId', 'N/A')}")
    print(f"  Type: {type(item)}")
    print(f"\n  Item attributes: {dir(item)}\n")
    
    # Get details
    print(f"\n{'='*60}")
    print(f"Getting details...")
    print(f"{'='*60}\n")
    
    details_provider = search_instance.get_item_details(item)
    details_model = await details_provider.get_content_model()
    
    print(f"✓ Details retrieved")
    print(f"  Type: {type(details_model)}")
    print(f"  Attributes: {dir(details_model)}\n")
    
    # Check for season data in various locations
    print(f"\n{'='*60}")
    print(f"Checking for season data...")
    print(f"{'='*60}\n")
    
    # Path 1: resData.resource.seasons
    if hasattr(details_model, 'resData'):
        print("✓ Has resData")
        resData = details_model.resData
        print(f"  resData type: {type(resData)}")
        print(f"  resData attributes: {dir(resData)}\n")
        
        if hasattr(resData, 'resource'):
            print("  ✓ Has resData.resource")
            resource = resData.resource
            print(f"    resource type: {type(resource)}")
            print(f"    resource attributes: {dir(resource)}\n")
            
            if hasattr(resource, 'seasons'):
                print("    ✓ Has resData.resource.seasons")
                seasons = resource.seasons
                print(f"      seasons type: {type(seasons)}")
                print(f"      seasons length: {len(seasons) if seasons else 0}")
                if seasons:
                    print(f"      First season: {seasons[0]}")
                    print(f"      First season type: {type(seasons[0])}")
                    if hasattr(seasons[0], '__dict__'):
                        print(f"      First season dict: {seasons[0].__dict__}")
            else:
                print("    ❌ No resData.resource.seasons")
        
        if hasattr(resData, 'seasons'):
            print("  ✓ Has resData.seasons")
            seasons = resData.seasons
            print(f"    seasons type: {type(seasons)}")
            print(f"    seasons length: {len(seasons) if seasons else 0}")
        else:
            print("  ❌ No resData.seasons")
    else:
        print("❌ No resData")
    
    # Path 2: resource.seasons
    if hasattr(details_model, 'resource'):
        print("\n✓ Has resource")
        resource = details_model.resource
        if hasattr(resource, 'seasons'):
            print("  ✓ Has resource.seasons")
            seasons = resource.seasons
            print(f"    seasons: {seasons}")
        else:
            print("  ❌ No resource.seasons")
    else:
        print("\n❌ No resource")
    
    # Path 3: data.seasons
    if hasattr(details_model, 'data'):
        print("\n✓ Has data")
        data = details_model.data
        if hasattr(data, 'seasons'):
            print("  ✓ Has data.seasons")
            seasons = data.seasons
            print(f"    seasons: {seasons}")
        else:
            print("  ❌ No data.seasons")
    else:
        print("\n❌ No data")
    
    # Try to convert to dict and print
    print(f"\n{'='*60}")
    print(f"Raw details_model as dict (if possible):")
    print(f"{'='*60}\n")
    try:
        if hasattr(details_model, 'model_dump'):
            details_dict = details_model.model_dump()
            print(json.dumps(details_dict, indent=2, default=str))
        elif hasattr(details_model, '__dict__'):
            print(json.dumps(details_model.__dict__, indent=2, default=str))
        else:
            print(f"Cannot convert to dict: {details_model}")
    except Exception as e:
        print(f"Error converting to dict: {e}")
    
    await session.aclose()

if __name__ == "__main__":
    asyncio.run(test_homepage_item())
