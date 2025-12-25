from moviebox_api import Session, Homepage
import asyncio

async def inspect():
    with open('homelist_output.txt', 'w', encoding='utf-8') as f:
        try:
            session = Session()
            homepage = Homepage(session=session)
            content = await homepage.get_content_model()
            
            if content.homeList:
                f.write(f"homeList length: {len(content.homeList)}\n")
                first_group = content.homeList[0]
                f.write(f"First group type: {type(first_group)}\n")
                f.write("First group attributes:\n")
                for attr in dir(first_group):
                    if not attr.startswith('_'):
                        f.write(f"{attr}\n")
                        
                # Check for items/list inside group
                if hasattr(first_group, 'list'):
                     f.write(f"Group list length: {len(first_group.list)}\n")
                     if first_group.list:
                         f.write(f"First item in group: {first_group.list[0]}\n")
            else:
                f.write("homeList is empty\n")
                
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(inspect())
