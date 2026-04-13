try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("ChatGoogleGenerativeAI imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")

try:
    from langchain_core.prompts import ChatPromptTemplate
    print("ChatPromptTemplate imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")

try:
    import google.generativeai as genai
    print("google.generativeai imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
