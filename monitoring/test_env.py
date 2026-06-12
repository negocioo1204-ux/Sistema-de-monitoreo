from dotenv import load_dotenv
import os

load_dotenv()
print("OMADA_BASE_URL:", os.getenv("OMADA_BASE_URL"))
print("OMADA_CLIENT_ID:", os.getenv("OMADA_CLIENT_ID"))
print("OMADA_CLIENT_SECRET:", os.getenv("OMADA_CLIENT_SECRET"))
print("OMADA_OMADAC_ID:", os.getenv("OMADA_OMADAC_ID"))