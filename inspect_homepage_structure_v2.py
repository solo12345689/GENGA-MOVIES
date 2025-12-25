from moviebox_api import Session, Homepage
import asyncio

async def inspect():
    with open('model_output.txt', 'w', encoding='utf-8') as f:
        try:
            session = Session()
            homepage = Homepage(session=session)
            content = await homepage.get_content_model()
            f.write(f"Type: {type(content)}\n")
            f.write("Attributes:\n")
            for attr in dir(content):
                if not attr.startswith('_'):
                    f.write(f"{attr}\n")
            
            if hasattr(content, 'model_dump'):
                f.write(f"\nDump keys: {list(content.model_dump().keys())}\n")
            elif hasattr(content, 'dict'):
                f.write(f"\nDict keys: {list(content.dict().keys())}\n")
                
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(inspect())
