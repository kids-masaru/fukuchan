try:
    from google import genai
    print("google.genai is installed.")
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("API Key not found.")
    else:
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents="Hello, confirm you are Gemini 3.",
            )
            print("Response:", response.text)
        except Exception as e:
            print("Error calling API:", e)
            
except ImportError:
    print("google.genai is NOT installed.")
    # Fallback check for old lib
    import google.generativeai as old_genai
    print("google.generativeai is installed version:", old_genai.__version__)
