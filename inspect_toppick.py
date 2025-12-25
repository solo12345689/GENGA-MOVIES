from moviebox_api import Session, Homepage
import asyncio

async def inspect():
    with open('toppick_output.txt', 'w', encoding='utf-8') as f:
        try:
            session = Session()
            homepage = Homepage(session=session)
            content = await homepage.get_content_model()
            
            if content.topPickList:
                f.write(f"topPickList length: {len(content.topPickList)}\n")
                first_item = content.topPickList[0]
                f.write(f"First item type: {type(first_item)}\n")
                f.write("First item attributes:\n")
                for attr in dir(first_item):
                    if not attr.startswith('_'):
                        f.write(f"{attr}\n")
                        
                # It seems topPickList is a list of Items directly?
                # Or list of groups?
                if hasattr(first_item, 'title'):
                    f.write(f"Title: {first_item.title}\n")
            else:
                f.write("topPickList is empty\n")
                
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(inspect())
