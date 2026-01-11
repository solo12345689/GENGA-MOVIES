
try:
    import api
    print("Syntax OK")
except Exception as e:
    import traceback
    traceback.print_exc()
